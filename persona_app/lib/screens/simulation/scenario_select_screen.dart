import 'package:flutter/material.dart';
import '../../core/models/persona.dart';
import '../../core/api/simulation_service.dart';
import 'simulation_chat_screen.dart';

class ScenarioSelectScreen extends StatefulWidget {
  final Persona persona;

  const ScenarioSelectScreen({super.key, required this.persona});

  @override
  State<ScenarioSelectScreen> createState() => _ScenarioSelectScreenState();
}

class _ScenarioSelectScreenState extends State<ScenarioSelectScreen> {
  bool _loading = false;

  static const _scenarios = [
    {'type': 'apology', 'label': '사과하기', 'icon': Icons.handshake, 'desc': '잘못을 인정하고 사과하는 연습'},
    {'type': 'conflict', 'label': '갈등 해결', 'icon': Icons.people, 'desc': '의견 충돌 상황에서 대화 연습'},
    {'type': 'confession', 'label': '고백하기', 'icon': Icons.favorite, 'desc': '감정을 솔직하게 표현하는 연습'},
    {'type': 'daily', 'label': '일상 대화', 'icon': Icons.chat_bubble, 'desc': '자연스러운 일상 대화 연습'},
    {'type': 'comfort', 'label': '위로하기', 'icon': Icons.sentiment_satisfied, 'desc': '힘든 상황에 공감하고 위로하는 연습'},
    {'type': 'request', 'label': '부탁하기', 'icon': Icons.volunteer_activism, 'desc': '정중하게 부탁하는 연습'},
  ];

  Future<void> _startSimulation(Map<String, dynamic> scenario) async {
    setState(() => _loading = true);
    try {
      final sim = await simulationService.createChatSimulation(
        widget.persona.id,
        {'scenario_type': scenario['type'], 'persona_name': widget.persona.name},
      );
      if (mounted) {
        setState(() => _loading = false);
        Navigator.push(context, MaterialPageRoute(
          builder: (_) => SimulationChatScreen(simulation: sim, persona: widget.persona),
        ));
      }
    } catch (e) {
      if (mounted) {
        setState(() => _loading = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('시작 실패: $e')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('${widget.persona.name}와 시뮬레이션')),
      body: _loading
          ? const Center(child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
              CircularProgressIndicator(), SizedBox(height: 16), Text('시나리오 준비 중...')]))
          : ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: _scenarios.length,
              itemBuilder: (ctx, i) {
                final s = _scenarios[i];
                return Card(
                  child: ListTile(
                    leading: Icon(s['icon'] as IconData, size: 32, color: Theme.of(context).colorScheme.primary),
                    title: Text(s['label'] as String, style: const TextStyle(fontWeight: FontWeight.bold)),
                    subtitle: Text(s['desc'] as String),
                    trailing: const Icon(Icons.play_arrow),
                    onTap: () => _startSimulation(s),
                  ),
                );
              },
            ),
    );
  }
}
