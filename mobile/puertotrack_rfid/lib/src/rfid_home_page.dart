import 'package:flutter/material.dart';

import 'deteccion_rfid.dart';
import 'rfid_api_client.dart';

class RfidHomePage extends StatefulWidget {
  const RfidHomePage({super.key, this.apiClient});

  final RfidApiClient? apiClient;

  @override
  State<RfidHomePage> createState() => _RfidHomePageState();
}

class _RfidHomePageState extends State<RfidHomePage> {
  final _formKey = GlobalKey<FormState>();
  final _url = TextEditingController(text: 'http://127.0.0.1:8100');
  final _clave = TextEditingController();
  final _codigo = TextEditingController();
  final _lector = TextEditingController(text: 'LECTOR_MOVIL_01');
  late final RfidApiClient _apiClient;
  bool _enviando = false;
  bool _claveVisible = false;
  String? _mensaje;
  bool _exito = false;

  @override
  void initState() {
    super.initState();
    _apiClient = widget.apiClient ?? RfidApiClient();
  }

  @override
  void dispose() {
    _url.dispose();
    _clave.clear();
    _clave.dispose();
    _codigo.dispose();
    _lector.dispose();
    if (widget.apiClient == null) _apiClient.close();
    super.dispose();
  }

  Future<void> _simularLectura() async {
    if (_enviando || !_formKey.currentState!.validate()) return;
    FocusScope.of(context).unfocus();
    setState(() {
      _enviando = true;
      _mensaje = null;
    });

    try {
      final deteccion = DeteccionRfid.nueva(
        codigoContenedor: _codigo.text,
        lector: _lector.text,
      );
      final eventoId = await _apiClient.enviar(
        baseUrl: _url.text,
        claveDispositivo: _clave.text,
        deteccion: deteccion,
      );
      if (!mounted) return;
      setState(() {
        _exito = true;
        _mensaje =
            'Detección aceptada por MQTT. Evento: $eventoId. '
            'La habilitación del contenedor todavía no está confirmada.';
      });
    } on RfidApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _exito = false;
        _mensaje = error.message;
      });
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(
        title: const Text('PuertoTrack RFID'),
        backgroundColor: const Color(0xFF102C42),
        foregroundColor: Colors.white,
      ),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 540),
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Card(
                elevation: 1,
                color: Colors.white,
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Form(
                    key: _formKey,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Icon(Icons.sensors, size: 44, color: scheme.primary),
                        const SizedBox(height: 12),
                        Text(
                          'Simulador de lectura',
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.headlineSmall
                              ?.copyWith(
                                fontWeight: FontWeight.bold,
                                color: const Color(0xFF102C42),
                              ),
                        ),
                        const SizedBox(height: 8),
                        const Text(
                          'Envía una detección simulada al servicio RFID.',
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 28),
                        TextFormField(
                          controller: _codigo,
                          textCapitalization: TextCapitalization.characters,
                          maxLength: 20,
                          decoration: const InputDecoration(
                            labelText: 'Código del contenedor',
                            hintText: 'DEMOENTRADA',
                            prefixIcon: Icon(Icons.inventory_2_outlined),
                          ),
                          validator: (valor) =>
                              valor == null || valor.trim().isEmpty
                              ? 'Ingresa un código de contenedor.'
                              : null,
                        ),
                        const SizedBox(height: 12),
                        TextFormField(
                          controller: _lector,
                          maxLength: 64,
                          decoration: const InputDecoration(
                            labelText: 'Identificador del lector',
                            prefixIcon: Icon(Icons.nfc_outlined),
                          ),
                          validator: (valor) =>
                              valor == null || valor.trim().isEmpty
                              ? 'Ingresa un identificador de lector.'
                              : null,
                        ),
                        const Divider(height: 36),
                        Text(
                          'Conexión local',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 14),
                        TextFormField(
                          controller: _url,
                          keyboardType: TextInputType.url,
                          autocorrect: false,
                          decoration: const InputDecoration(
                            labelText: 'URL del servicio RFID',
                            hintText: 'http://127.0.0.1:8100',
                            prefixIcon: Icon(Icons.link),
                          ),
                          validator: (valor) {
                            try {
                              RfidApiClient.validarUrl(valor ?? '');
                              return null;
                            } on RfidApiException catch (error) {
                              return error.message;
                            }
                          },
                        ),
                        const SizedBox(height: 16),
                        TextFormField(
                          controller: _clave,
                          obscureText: !_claveVisible,
                          autocorrect: false,
                          enableSuggestions: false,
                          decoration: InputDecoration(
                            labelText: 'Clave temporal del dispositivo',
                            prefixIcon: const Icon(Icons.key_outlined),
                            suffixIcon: IconButton(
                              tooltip: _claveVisible
                                  ? 'Ocultar clave'
                                  : 'Mostrar clave',
                              onPressed: () => setState(
                                () => _claveVisible = !_claveVisible,
                              ),
                              icon: Icon(
                                _claveVisible
                                    ? Icons.visibility_off
                                    : Icons.visibility,
                              ),
                            ),
                          ),
                          validator: (valor) => valor == null || valor.isEmpty
                              ? 'Ingresa la clave temporal.'
                              : null,
                        ),
                        const SizedBox(height: 24),
                        FilledButton.icon(
                          onPressed: _enviando ? null : _simularLectura,
                          icon: _enviando
                              ? const SizedBox(
                                  width: 18,
                                  height: 18,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: Colors.white,
                                  ),
                                )
                              : const Icon(Icons.sensors),
                          label: Text(
                            _enviando ? 'Enviando…' : 'Simular lectura RFID',
                          ),
                        ),
                        if (_mensaje != null) ...[
                          const SizedBox(height: 20),
                          Semantics(
                            liveRegion: true,
                            child: Container(
                              padding: const EdgeInsets.all(14),
                              decoration: BoxDecoration(
                                color: _exito
                                    ? const Color(0xFFE6F5EF)
                                    : const Color(0xFFFCEBE9),
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: Text(
                                _mensaje!,
                                key: const Key('resultado-deteccion'),
                                style: TextStyle(
                                  color: _exito
                                      ? const Color(0xFF126447)
                                      : const Color(0xFF9B342D),
                                ),
                              ),
                            ),
                          ),
                        ],
                        const SizedBox(height: 18),
                        Text(
                          'HTTP 202 confirma la publicación en Mosquitto. '
                          'La identificación y la decisión de acceso ocurren después.',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
