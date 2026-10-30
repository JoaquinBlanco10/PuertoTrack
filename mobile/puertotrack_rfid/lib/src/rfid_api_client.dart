import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import 'deteccion_rfid.dart';

class RfidApiException implements Exception {
  const RfidApiException(this.message);
  final String message;

  @override
  String toString() => message;
}

class RfidApiClient {
  RfidApiClient({
    http.Client? client,
    this.timeout = const Duration(seconds: 8),
  }) : _client = client ?? http.Client(),
       _ownsClient = client == null;

  final http.Client _client;
  final bool _ownsClient;
  final Duration timeout;

  void close() {
    if (_ownsClient) _client.close();
  }

  static Uri validarUrl(String baseUrl, {bool? debugMode}) {
    final uri = Uri.tryParse(baseUrl.trim());
    if (uri == null ||
        uri.host.isEmpty ||
        uri.hasQuery ||
        uri.hasFragment ||
        uri.userInfo.isNotEmpty ||
        (uri.path.isNotEmpty && uri.path != '/')) {
      throw const RfidApiException('Ingresa la URL base del servidor RFID.');
    }
    final esDebug = debugMode ?? kDebugMode;
    final esHostDeDesarrollo = {
      '127.0.0.1',
      'localhost',
      '::1',
      '10.0.2.2',
    }.contains(uri.host);
    if (uri.scheme != 'https' &&
        !(esDebug && uri.scheme == 'http' && esHostDeDesarrollo)) {
      throw const RfidApiException(
        'Usa HTTPS; HTTP local solo está permitido en modo debug.',
      );
    }
    return uri.replace(path: '/detecciones');
  }

  Future<String> enviar({
    required String baseUrl,
    required String claveDispositivo,
    required DeteccionRfid deteccion,
  }) async {
    final uri = validarUrl(baseUrl);
    if (claveDispositivo.isEmpty) {
      throw const RfidApiException(
        'Ingresa la clave temporal del dispositivo.',
      );
    }
    late final http.Response respuesta;
    try {
      respuesta = await _client
          .post(
            uri,
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json',
              'X-PuertoTrack-Device-Key': claveDispositivo,
            },
            body: jsonEncode(deteccion.toJson()),
          )
          .timeout(timeout);
    } on TimeoutException {
      throw const RfidApiException(
        'Tiempo de espera agotado. Revisa la conexión.',
      );
    } on SocketException {
      throw const RfidApiException('No se pudo conectar con PuertoTrack RFID.');
    } on http.ClientException {
      throw const RfidApiException('No se pudo conectar con PuertoTrack RFID.');
    }

    switch (respuesta.statusCode) {
      case 202:
        try {
          final cuerpo = jsonDecode(respuesta.body);
          if (cuerpo is Map<String, dynamic> &&
              cuerpo['estado'] == 'aceptado' &&
              cuerpo['evento_id'] == deteccion.eventoId) {
            return deteccion.eventoId;
          }
        } on FormatException {
          // No se muestra una respuesta inesperada del servidor.
        }
        throw const RfidApiException(
          'El servidor devolvió una respuesta inesperada.',
        );
      case 401:
        throw const RfidApiException(
          'Clave de dispositivo incorrecta o ausente.',
        );
      case 422:
        throw const RfidApiException(
          'La detección no cumple el contrato RFID.',
        );
      case 503:
        throw const RfidApiException(
          'El servicio RFID o Mosquitto no está disponible.',
        );
      default:
        throw RfidApiException(
          'No se pudo enviar la detección (HTTP ${respuesta.statusCode}).',
        );
    }
  }
}
