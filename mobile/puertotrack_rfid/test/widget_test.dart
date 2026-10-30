import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:puertotrack_rfid/src/rfid_api_client.dart';
import 'package:puertotrack_rfid/src/rfid_home_page.dart';

void main() {
  testWidgets('valida campos y confirma solo publicación MQTT', (tester) async {
    final cliente = RfidApiClient(
      client: MockClient((solicitud) async {
        final body = jsonDecode(solicitud.body) as Map<String, dynamic>;
        expect(body['codigo_contenedor'], 'DEMOENTRADA');
        expect(body['lector'], 'LECTOR_MOVIL_01');
        return http.Response(
          jsonEncode({'estado': 'aceptado', 'evento_id': body['evento_id']}),
          202,
        );
      }),
    );

    await tester.pumpWidget(
      MaterialApp(home: RfidHomePage(apiClient: cliente)),
    );
    expect(find.text('LECTOR_MOVIL_01'), findsOneWidget);
    await tester.ensureVisible(find.text('Simular lectura RFID'));
    await tester.tap(find.text('Simular lectura RFID'));
    await tester.pump();
    expect(find.text('Ingresa un código de contenedor.'), findsOneWidget);

    await tester.enterText(find.byType(TextFormField).at(0), 'demoentrada');
    await tester.enterText(find.byType(TextFormField).at(3), 'clave-temporal');
    await tester.ensureVisible(find.text('Simular lectura RFID'));
    await tester.tap(find.text('Simular lectura RFID'));
    await tester.pumpAndSettle();

    expect(find.textContaining('Detección aceptada por MQTT.'), findsOneWidget);
    expect(find.textContaining('todavía no está confirmada'), findsOneWidget);
  });

  testWidgets('deshabilita el envío pendiente y muestra fallo 503', (
    tester,
  ) async {
    final respuesta = Completer<http.Response>();
    final cliente = RfidApiClient(client: MockClient((_) => respuesta.future));
    await tester.pumpWidget(
      MaterialApp(home: RfidHomePage(apiClient: cliente)),
    );

    await tester.enterText(find.byType(TextFormField).at(0), 'DEMOENTRADA');
    await tester.enterText(find.byType(TextFormField).at(3), 'clave-temporal');
    await tester.ensureVisible(find.text('Simular lectura RFID'));
    await tester.tap(find.text('Simular lectura RFID'));
    await tester.pump();

    expect(find.text('Enviando…'), findsOneWidget);
    expect(
      tester.widget<FilledButton>(
        find.byWidgetPredicate((widget) => widget is FilledButton),
      ).onPressed,
      isNull,
    );

    respuesta.complete(http.Response('{}', 503));
    await tester.pumpAndSettle();
    expect(find.textContaining('Mosquitto no está disponible'), findsOneWidget);
    expect(find.text('Simular lectura RFID'), findsOneWidget);
  });
}
