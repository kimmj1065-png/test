import 'package:flutter/material.dart';
import 'core/auth/auth_service.dart';
import 'screens/auth/login_screen.dart';
import 'screens/auth/register_screen.dart';
import 'screens/persona/persona_list_screen.dart';

void main() {
  runApp(const PersonaApp());
}

class PersonaApp extends StatelessWidget {
  const PersonaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '페르소나 시뮬레이션',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF6750A4)),
        useMaterial3: true,
      ),
      home: const AppRoot(),
    );
  }
}

class AppRoot extends StatefulWidget {
  const AppRoot({super.key});

  @override
  State<AppRoot> createState() => _AppRootState();
}

class _AppRootState extends State<AppRoot> {
  bool _checkingAuth = true;
  bool _loggedIn = false;
  bool _showRegister = false;

  @override
  void initState() {
    super.initState();
    _checkAuth();
  }

  Future<void> _checkAuth() async {
    final loggedIn = await authService.isLoggedIn();
    if (mounted) setState(() { _loggedIn = loggedIn; _checkingAuth = false; });
  }

  @override
  Widget build(BuildContext context) {
    if (_checkingAuth) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    if (_loggedIn) {
      return PersonaListScreen(onLogout: () => setState(() => _loggedIn = false));
    }
    if (_showRegister) {
      return RegisterScreen(
        onRegister: () => setState(() { _loggedIn = true; _showRegister = false; }),
        onGoLogin: () => setState(() => _showRegister = false),
      );
    }
    return LoginScreen(
      onLogin: () => setState(() => _loggedIn = true),
      onGoRegister: () => setState(() => _showRegister = true),
    );
  }
}
