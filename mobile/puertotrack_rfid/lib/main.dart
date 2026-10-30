import 'package:flutter/material.dart';

import 'src/rfid_home_page.dart';

void main() => runApp(const PuertoTrackRfidApp());

class PuertoTrackRfidApp extends StatelessWidget {
  const PuertoTrackRfidApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'PuertoTrack RFID',
    debugShowCheckedModeBanner: false,
    theme: ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: const Color(0xFF087F8C),
        primary: const Color(0xFF087F8C),
        surface: const Color(0xFFF6F9FC),
      ),
      scaffoldBackgroundColor: const Color(0xFFF6F9FC),
      inputDecorationTheme: InputDecorationTheme(
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 16,
        ),
      ),
    ),
    home: const RfidHomePage(),
  );
}
