import 'package:flutter/material.dart';
import '../../core/auth/auth_service.dart';

class RegisterScreen extends StatefulWidget {
  final VoidCallback onRegister;
  final VoidCallback onGoLogin;

  const RegisterScreen({super.key, required this.onRegister, required this.onGoLogin});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _usernameCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  final _confirmCtrl = TextEditingController();
  bool _loading = false;
  String? _error;

  Future<void> _register() async {
    if (_passwordCtrl.text != _confirmCtrl.text) {
      setState(() => _error = '비밀번호가 일치하지 않습니다.');
      return;
    }
    setState(() { _loading = true; _error = null; });
    final ok = await authService.register(_usernameCtrl.text.trim(), _passwordCtrl.text);
    if (!mounted) return;
    setState(() => _loading = false);
    if (ok) {
      widget.onRegister();
    } else {
      setState(() => _error = '회원가입에 실패했습니다. 이미 존재하는 아이디일 수 있습니다.');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('회원가입')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TextField(
                controller: _usernameCtrl,
                decoration: const InputDecoration(labelText: '아이디', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _passwordCtrl,
                obscureText: true,
                decoration: const InputDecoration(labelText: '비밀번호', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _confirmCtrl,
                obscureText: true,
                decoration: const InputDecoration(labelText: '비밀번호 확인', border: OutlineInputBorder()),
              ),
              if (_error != null) ...[
                const SizedBox(height: 8),
                Text(_error!, style: const TextStyle(color: Colors.red)),
              ],
              const SizedBox(height: 24),
              ElevatedButton(
                onPressed: _loading ? null : _register,
                style: ElevatedButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 16)),
                child: _loading ? const CircularProgressIndicator() : const Text('회원가입'),
              ),
              const SizedBox(height: 12),
              TextButton(
                onPressed: widget.onGoLogin,
                child: const Text('이미 계정이 있으신가요? 로그인'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
