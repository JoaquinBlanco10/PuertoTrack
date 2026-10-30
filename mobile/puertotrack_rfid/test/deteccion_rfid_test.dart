import 'package:flutter_test/flutter_test.dart';
import 'package:puertotrack_rfid/src/deteccion_rfid.dart';

void main() {
  test('genera los cuatro campos exactos, UUID y fecha UTC', () {
    final deteccion = DeteccionRfid.nueva(
      codigoContenedor: ' demoentrada ',
      lector: ' LECTOR_MOVIL_01 ',
      ahora: DateTime.parse('2026-10-30T09:30:00-03:00'),
    );
    final json = deteccion.toJson();

    expect(json.keys.toSet(), {
      'evento_id',
      'codigo_contenedor',
      'lector',
      'fecha_utc',
    });
    expect(
      json['evento_id'],
      matches(
        RegExp(
          r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
        ),
      ),
    );
    expect(json['codigo_contenedor'], 'DEMOENTRADA');
    expect(json['lector'], 'LECTOR_MOVIL_01');
    expect(json['fecha_utc'], '2026-10-30T12:30:00.000Z');
  });
}
