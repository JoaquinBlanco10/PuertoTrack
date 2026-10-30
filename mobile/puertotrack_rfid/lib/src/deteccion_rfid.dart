import 'package:uuid/uuid.dart';

class DeteccionRfid {
  const DeteccionRfid({
    required this.eventoId,
    required this.codigoContenedor,
    required this.lector,
    required this.fechaUtc,
  });

  factory DeteccionRfid.nueva({
    required String codigoContenedor,
    required String lector,
    DateTime? ahora,
    String? eventoId,
  }) => DeteccionRfid(
    eventoId: eventoId ?? const Uuid().v4(),
    codigoContenedor: codigoContenedor.trim().toUpperCase(),
    lector: lector.trim(),
    fechaUtc: (ahora ?? DateTime.now()).toUtc(),
  );

  final String eventoId;
  final String codigoContenedor;
  final String lector;
  final DateTime fechaUtc;

  Map<String, String> toJson() => {
    'evento_id': eventoId,
    'codigo_contenedor': codigoContenedor,
    'lector': lector,
    'fecha_utc': fechaUtc.toIso8601String(),
  };
}
