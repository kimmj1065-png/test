class SimulationTurn {
  final String role;
  final String content;

  SimulationTurn({required this.role, required this.content});

  factory SimulationTurn.fromJson(Map<String, dynamic> json) => SimulationTurn(
        role: json['role'] as String,
        content: json['content'] as String,
      );
}

class Savepoint {
  final String id;
  final int turnIndex;
  final String label;

  Savepoint({required this.id, required this.turnIndex, required this.label});

  factory Savepoint.fromJson(Map<String, dynamic> json) => Savepoint(
        id: json['id'] as String,
        turnIndex: json['turn_index'] as int,
        label: json['label'] as String? ?? '저장점',
      );
}

class ChatSimulation {
  final String id;
  final String personaId;
  final String scenarioType;
  final Map<String, dynamic> scenarioConfig;
  final List<SimulationTurn> turns;
  final List<Savepoint> savepoints;
  final Map<String, dynamic> feedback;
  final DateTime createdAt;

  ChatSimulation({
    required this.id,
    required this.personaId,
    required this.scenarioType,
    required this.scenarioConfig,
    required this.turns,
    required this.savepoints,
    required this.feedback,
    required this.createdAt,
  });

  factory ChatSimulation.fromJson(Map<String, dynamic> json) => ChatSimulation(
        id: json['id'] as String,
        personaId: json['persona_id'] as String,
        scenarioType: json['scenario_type'] as String? ?? '',
        scenarioConfig: (json['scenario_config'] as Map<String, dynamic>?) ?? {},
        turns: (json['turns'] as List<dynamic>? ?? [])
            .map((t) => SimulationTurn.fromJson(t as Map<String, dynamic>))
            .toList(),
        savepoints: (json['savepoints'] as List<dynamic>? ?? [])
            .map((s) => Savepoint.fromJson(s as Map<String, dynamic>))
            .toList(),
        feedback: (json['feedback'] as Map<String, dynamic>?) ?? {},
        createdAt: DateTime.parse(json['created_at'] as String),
      );

}
