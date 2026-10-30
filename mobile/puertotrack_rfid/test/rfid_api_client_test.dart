import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:puertotrack_rfid/src/deteccion_rfid.dart';
import 'package:puertotrack_rfid/src/rfid_api_client.dart';

void main() {
  const eventoId = '550e8400-e29b-41d4-a716-446655440000';
  final deteccion = DeteccionRfid.nueva(
    codigoContenedor: 'demoentrada',
    lector: 'LECTOR_MOVIL_01',
    eventoId: eventoId,
    ahora: DateTime.utc(2026, 10, 30, 12),
  );

  test('valida URL local solo para debug y HTTPS para release', () {
    expect(
      RfidApiClient.validarUrl(
        'http://127.0.0.1:8100',
        debugMode: true,
      ).toString(),
      'http://127.0.0.1:8100/detecciones',
    );
    expect(
      RfidApiClient.validarUrl(
        'https://rfid.example.test',
        debugMode: false,
      ).toString(),
      'https://rfid.example.test/detecciones',
    );
    expect(
      () => RfidApiClient.validarUrl('http://127.0.0.1:8100', debugMode: false),
      throwsA(isA<RfidApiException>()),
    );
    expect(
      () =>
          RfidApiClient.validarUrl('http://192.168.1.2:8100', debugMode: true),
      throwsA(isA<RfidApiException>()),
    );
    expect(
      () => RfidApiClient.validarUrl(
        'https://usuario@rfid.example.test',
        debugMode: true,
      ),
      throwsA(isA<RfidApiException>()),
    );
  });

  test(
    'envía contrato exacto con clave en cabecera y acepta 202 coincidente',
    () async {
      final cliente = RfidApiClient(
        client: MockClient((solicitud) async {
          expect(solicitud.method, 'POST');
          expect(solicitud.url.path, '/detecciones');
          expect(
            solicitud.headers['X-PuertoTrack-Device-Key'],
            'clave-temporal',
          );
          expect(
            solicitud.headers['Content-Type'],
            contains('application/json'),
          );
          expect(jsonDecode(solicitud.body), deteccion.toJson());
          return http.Response(
            jsonEncode({'estado': 'aceptado', 'evento_id': eventoId}),
            202,
          );
        }),
      );

      final recibido = await cliente.enviar(
        baseUrl: 'http://127.0.0.1:8100',
        claveDispositivo: 'clave-temporal',
        deteccion: deteccion,
      );

      expect(recibido, eventoId);
    },
  );

  for (final caso in <int, String>{
    401: 'Clave de dispositivo incorrecta',
    422: 'contrato RFID',
    503: 'Mosquitto no está disponible',
  }.entries) {
    test('explica HTTP ${caso.key}', () async {
      final cliente = RfidApiClient(
        client: MockClient((_) async => http.Response('{}', caso.key)),
      );
      expect(
        () => cliente.enviar(
          baseUrl: 'http://127.0.0.1:8100',
          claveDispositivo: 'clave-temporal',
          deteccion: deteccion,
        ),
        throwsA(
          isA<RfidApiException>().having(
            (e) => e.message,
            'mensaje',
            contains(caso.value),
          ),
        ),
      );
    });
  }

  test('no presenta 202 ajeno como confirmación válida', () async {
    final cliente = RfidApiClient(
      client: MockClient(
        (_) async => http.Response(
          jsonEncode({'estado': 'aceptado', 'evento_id': 'otro'}),
          202,
        ),
      ),
    );
    expect(
      () => cliente.enviar(
        baseUrl: 'http://127.0.0.1:8100',
        claveDispositivo: 'clave-temporal',
        deteccion: deteccion,
      ),
      throwsA(isA<RfidApiException>()),
    );
  });

  test('explica fallo de conexión y tiempo de espera', () async {
    final desconectado = RfidApiClient(
      client: MockClient((_) async {
        throw http.ClientException('sin conexión');
      }),
    );
    expect(
      () => desconectado.enviar(
        baseUrl: 'http://127.0.0.1:8100',
        claveDispositivo: 'clave-temporal',
        deteccion: deteccion,
      ),
      throwsA(
        isA<RfidApiException>().having(
          (e) => e.message,
          'mensaje',
          contains('conectar'),
        ),
      ),
    );

    final lento = RfidApiClient(
      client: MockClient((_) => Completer<http.Response>().future),
      timeout: const Duration(milliseconds: 10),
    );
    expect(
      () => lento.enviar(
        baseUrl: 'http://127.0.0.1:8100',
        claveDispositivo: 'clave-temporal',
        deteccion: deteccion,
      ),
      throwsA(
        isA<RfidApiException>().having(
          (e) => e.message,
          'mensaje',
          contains('espera'),
        ),
      ),
    );
  });
}
