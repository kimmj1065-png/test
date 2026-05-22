import '../models/simulation.dart';
import 'api_client.dart';

class ChatSimulationService {
  Future<ChatSimulation> createChatSimulation(String personaId, Map<String, dynamic> scenarioConfig) async {
    final response = await apiClient.post('/simulations', data: {
      'persona_id': personaId,
      'scenario_config': scenarioConfig,
    });
    return ChatSimulation.fromJson(response.data as Map<String, dynamic>);
  }

  Future<ChatSimulation> sendTurn(String simulationId, String message) async {
    final response = await apiClient.post('/simulations/$simulationId/turn', data: {
      'message': message,
    });
    return ChatSimulation.fromJson(response.data as Map<String, dynamic>);
  }

  Future<ChatSimulation> createSavepoint(String simulationId) async {
    final response = await apiClient.post('/simulations/$simulationId/savepoint');
    return ChatSimulation.fromJson(response.data as Map<String, dynamic>);
  }

  Future<ChatSimulation> restoreSavepoint(String simulationId, String savepointId) async {
    final response = await apiClient.post('/simulations/$simulationId/restore/$savepointId');
    return ChatSimulation.fromJson(response.data as Map<String, dynamic>);
  }

  Future<ChatSimulation> getFeedback(String simulationId) async {
    final response = await apiClient.post('/simulations/$simulationId/feedback');
    return ChatSimulation.fromJson(response.data as Map<String, dynamic>);
  }

  Future<List<ChatSimulation>> getChatSimulations() async {
    final response = await apiClient.get('/simulations');
    final list = response.data['simulations'] as List<dynamic>;
    return list.map((e) => ChatSimulation.fromJson(e as Map<String, dynamic>)).toList();
  }
}

final simulationService = ChatSimulationService();
