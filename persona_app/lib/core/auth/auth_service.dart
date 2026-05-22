import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../api/api_client.dart';

class AuthService {
  static const _storage = FlutterSecureStorage();

  Future<bool> login(String username, String password) async {
    try {
      final response = await apiClient.post('/auth/login', data: {
        'username': username,
        'password': password,
      });
      final token = response.data['access_token'] as String;
      await _storage.write(key: 'access_token', value: token);
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<bool> register(String username, String password) async {
    try {
      await apiClient.post('/auth/register', data: {
        'username': username,
        'password': password,
      });
      return await login(username, password);
    } catch (_) {
      return false;
    }
  }

  Future<void> logout() async {
    await _storage.delete(key: 'access_token');
  }

  Future<bool> isLoggedIn() async {
    final token = await _storage.read(key: 'access_token');
    return token != null;
  }
}

final authService = AuthService();
