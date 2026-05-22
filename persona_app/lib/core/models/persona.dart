class Persona {
  final String id;
  final String name;
  final Map<String, dynamic> profileJson;
  final DateTime createdAt;

  Persona({
    required this.id,
    required this.name,
    required this.profileJson,
    required this.createdAt,
  });

  factory Persona.fromJson(Map<String, dynamic> json) => Persona(
        id: json['id'] as String,
        name: json['name'] as String,
        profileJson: (json['profile_json'] as Map<String, dynamic>?) ?? {},
        createdAt: DateTime.parse(json['created_at'] as String),
      );
}
