import 'package:dio/dio.dart';
import '../models/persona.dart';
import 'api_client.dart';

class PersonaService {
  Future<List<Persona>> getPersonas() async {
    final response = await apiClient.get('/personas');
    final list = response.data['personas'] as List<dynamic>;
    return list.map((e) => Persona.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<Persona> getPersona(String id) async {
    final response = await apiClient.get('/personas/$id');
    return Persona.fromJson(response.data as Map<String, dynamic>);
  }

  Future<List<Persona>> uploadKakaoTalk(String filePath) async {
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(filePath),
    });
    final response = await apiClient.postFormData('/personas/upload', formData);
    final list = response.data['personas'] as List<dynamic>;
    return list.map((e) => Persona.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<Persona> updatePersona(String id, String filePath) async {
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(filePath),
    });
    final response = await apiClient.postFormData('/personas/$id/update', formData);
    return Persona.fromJson(response.data as Map<String, dynamic>);
  }

  Future<void> deletePersona(String id) async {
    await apiClient.delete('/personas/$id');
  }
}

final personaService = PersonaService();
