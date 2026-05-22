import 'package:flutter/material.dart';
import '../../core/models/simulation.dart';
import '../../core/models/persona.dart';

class FeedbackScreen extends StatelessWidget {
  final ChatSimulation simulation;
  final Persona persona;

  const FeedbackScreen({super.key, required this.simulation, required this.persona});

  @override
  Widget build(BuildContext context) {
    final fb = simulation.feedback;
    return Scaffold(
      appBar: AppBar(title: Text('${persona.name}와의 대화 피드백')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (fb.isEmpty)
              const Center(child: Text('피드백이 없습니다.'))
            else ...[
              _scoreCard(fb),
              const SizedBox(height: 16),
              if (fb['strengths'] != null) _listCard('잘한 점', fb['strengths'] as List, Colors.green),
              const SizedBox(height: 16),
              if (fb['improvements'] != null) _listCard('개선할 점', fb['improvements'] as List, Colors.orange),
              const SizedBox(height: 16),
              if (fb['summary'] != null)
                Card(child: Padding(padding: const EdgeInsets.all(16), child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('총평', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                    const SizedBox(height: 8),
                    Text(fb['summary'] as String),
                  ],
                ))),
            ],
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () => Navigator.of(context).popUntil((route) => route.isFirst),
              child: const Text('홈으로'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _scoreCard(Map<String, dynamic> fb) {
    final score = (fb['score'] as num?)?.toInt();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(children: [
          const Text('대화 점수', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          if (score != null) ...[
            Text('$score', style: const TextStyle(fontSize: 48, fontWeight: FontWeight.bold)),
            Text('/100', style: const TextStyle(color: Colors.grey)),
            const SizedBox(height: 8),
            LinearProgressIndicator(value: score / 100, minHeight: 8),
          ],
        ]),
      ),
    );
  }

  Widget _listCard(String title, List items, Color color) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: color)),
            const SizedBox(height: 8),
            ...items.map((item) => Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Row(children: [
                Icon(Icons.circle, size: 8, color: color),
                const SizedBox(width: 8),
                Expanded(child: Text(item.toString())),
              ]),
            )),
          ],
        ),
      ),
    );
  }
}
