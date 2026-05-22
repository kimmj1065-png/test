import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import '../../core/models/persona.dart';
import '../../core/api/persona_service.dart';
import '../simulation/scenario_select_screen.dart';

class PersonaDetailScreen extends StatefulWidget {
  final String personaId;

  const PersonaDetailScreen({super.key, required this.personaId});

  @override
  State<PersonaDetailScreen> createState() => _PersonaDetailScreenState();
}

class _PersonaDetailScreenState extends State<PersonaDetailScreen> {
  Persona? _persona;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final p = await personaService.getPersona(widget.personaId);
      if (mounted) setState(() { _persona = p; _loading = false; });
    } catch (e) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _update() async {
    final result = await FilePicker.platform.pickFiles(type: FileType.custom, allowedExtensions: ['txt']);
    if (result == null || result.files.single.path == null) return;

    if (!mounted) return;
    showDialog(context: context, barrierDismissible: false,
      builder: (_) => const AlertDialog(content: Row(children: [CircularProgressIndicator(), SizedBox(width: 16), Text('업데이트 중...')])));

    try {
      final updated = await personaService.updatePersona(widget.personaId, result.files.single.path!);
      if (mounted) {
        Navigator.pop(context);
        setState(() => _persona = updated);
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('페르소나가 업데이트되었습니다.')));
      }
    } catch (e) {
      if (mounted) {
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('업데이트 실패: $e')));
      }
    }
  }

  Future<void> _delete() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('삭제 확인'),
        content: Text('${_persona?.name} 페르소나를 삭제하시겠습니까?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('취소')),
          TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('삭제', style: TextStyle(color: Colors.red))),
        ],
      ),
    );
    if (confirm != true) return;
    await personaService.deletePersona(widget.personaId);
    if (mounted) Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_persona?.name ?? '페르소나'),
        actions: [
          if (_persona != null) ...[
            IconButton(icon: const Icon(Icons.upload_file), onPressed: _update, tooltip: '데이터 추가'),
            IconButton(icon: const Icon(Icons.delete), onPressed: _delete, tooltip: '삭제'),
          ],
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _persona == null
              ? const Center(child: Text('로드 실패'))
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      _ProfileCard(persona: _persona!),
                      const SizedBox(height: 24),
                      ElevatedButton.icon(
                        onPressed: () => Navigator.push(context, MaterialPageRoute(
                          builder: (_) => ScenarioSelectScreen(persona: _persona!),
                        )),
                        icon: const Icon(Icons.chat),
                        label: const Text('시뮬레이션 시작'),
                        style: ElevatedButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 16)),
                      ),
                    ],
                  ),
                ),
    );
  }
}

class _ProfileCard extends StatelessWidget {
  final Persona persona;

  const _ProfileCard({required this.persona});

  @override
  Widget build(BuildContext context) {
    final p = persona.profileJson;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              CircleAvatar(radius: 32, child: Text(persona.name[0], style: const TextStyle(fontSize: 28))),
              const SizedBox(width: 16),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(persona.name, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                Text(p['summary'] as String? ?? '', style: const TextStyle(color: Colors.grey)),
              ])),
            ]),
            const Divider(height: 32),
            _statRow('말투', p['speech_style'] as String? ?? '-'),
            _statRow('주도성', '${((p['initiative_score'] as num?)?.toInt() ?? 0)}점'),
            if (p['top_expressions'] != null) ...[
              const SizedBox(height: 8),
              const Text('자주 쓰는 표현', style: TextStyle(fontWeight: FontWeight.bold)),
              const SizedBox(height: 4),
              Wrap(spacing: 8, children: (p['top_expressions'] as List<dynamic>)
                .map((e) => Chip(label: Text(e.toString())))
                .toList()),
            ],
          ],
        ),
      ),
    );
  }

  Widget _statRow(String label, String value) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 4),
    child: Row(children: [
      SizedBox(width: 80, child: Text(label, style: const TextStyle(color: Colors.grey))),
      Text(value, style: const TextStyle(fontWeight: FontWeight.w500)),
    ]),
  );
}
