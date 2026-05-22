import 'package:flutter/material.dart';
import '../../core/auth/auth_service.dart';

class LoginScreen extends StatefulWidget {
  final VoidCallback onLogin;
  final VoidCallback onGoRegister;

  const LoginScreen({super.key, required this.onLogin, required this.onGoRegister});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _usernameCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  bool _loading = false;
  String? _error;

  Future<void> _login() async {
    setState(() { _loading = true; _error = null; });
    final ok = await authService.login(_usernameCtrl.text.trim(), _passwordCtrl.text);
    if (!mounted) return;
    setState(() => _loading = false);
    if (ok) {
      widget.onLogin();
    } else {
      setState(() => _error = '아이디 또는 비밀번호가 틀렸습니다.');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text('페르소나 시뮬레이션', style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold), textAlign: TextAlign.center),
              const SizedBox(height: 8),
              const Text('나를 닮은 AI와 대화 연습', style: TextStyle(color: Colors.grey), textAlign: TextAlign.center),
              const SizedBox(height: 48),
              TextField(
                controller: _usernameCtrl,
                decoration: const InputDecoration(labelText: '아이디', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _passwordCtrl,
                obscureText: true,
                decoration: const InputDecoration(labelText: '비밀번호', border: OutlineInputBorder()),
                onSubmitted: (_) => _login(),
              ),
              if (_error != null) ...[
                const SizedBox(height: 8),
                Text(_error!, style: const TextStyle(color: Colors.red)),
              ],
              const SizedBox(height: 24),
              ElevatedButton(
                onPressed: _loading ? null : _login,
                style: ElevatedButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 16)),
                child: _loading ? const CircularProgressIndicator() : const Text('로그인'),
              ),
              const SizedBox(height: 12),
              TextButton(
                onPressed: widget.onGoRegister,
                child: const Text('계정이 없으신가요? 회원가입'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
