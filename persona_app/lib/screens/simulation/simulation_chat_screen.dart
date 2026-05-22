import 'package:flutter/material.dart';
import '../../core/models/simulation.dart';
import '../../core/models/persona.dart';
import '../../core/api/simulation_service.dart';
import 'feedback_screen.dart';

class SimulationChatScreen extends StatefulWidget {
  final ChatSimulation simulation;
  final Persona persona;

  const SimulationChatScreen({super.key, required this.simulation, required this.persona});


  @override
  State<SimulationChatScreen> createState() => _SimulationChatScreenState();
}

class _SimulationChatScreenState extends State<SimulationChatScreen> {
  late ChatSimulation _sim;
  final _msgCtrl = TextEditingController();
  final _scrollCtrl = ScrollController();
  bool _sending = false;

  @override
  void initState() {
    super.initState();
    _sim = widget.simulation;
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(_scrollCtrl.position.maxScrollExtent,
            duration: const Duration(milliseconds: 300), curve: Curves.easeOut);
      }
    });
  }

  Future<void> _send() async {
    final msg = _msgCtrl.text.trim();
    if (msg.isEmpty || _sending) return;
    _msgCtrl.clear();
    setState(() => _sending = true);
    try {
      final updated = await simulationService.sendTurn(_sim.id, msg);
      if (mounted) setState(() { _sim = updated; _sending = false; });
      _scrollToBottom();
    } catch (e) {
      if (mounted) setState(() => _sending = false);
    }
  }

  Future<void> _savepoint() async {
    try {
      final updated = await simulationService.createSavepoint(_sim.id);
      if (mounted) {
        setState(() => _sim = updated);
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('저장점이 생성되었습니다.')));
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('저장 실패: $e')));
    }
  }

  Future<void> _showSavepoints() async {
    if (_sim.savepoints.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('저장점이 없습니다.')));
      return;
    }
    final selected = await showDialog<Savepoint>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('저장점으로 돌아가기'),
        content: SizedBox(
          width: double.maxFinite,
          child: ListView.builder(
            shrinkWrap: true,
            itemCount: _sim.savepoints.length,
            itemBuilder: (ctx, i) {
              final sp = _sim.savepoints[i];
              return ListTile(
                title: Text(sp.label),
                subtitle: Text('${sp.turnIndex}번째 대화'),
                onTap: () => Navigator.pop(ctx, sp),
              );
            },
          ),
        ),
      ),
    );
    if (selected == null || !mounted) return;
    try {
      final updated = await simulationService.restoreSavepoint(_sim.id, selected.id);
      if (mounted) setState(() => _sim = updated);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('복원 실패: $e')));
    }
  }

  Future<void> _getFeedback() async {
    showDialog(context: context, barrierDismissible: false,
      builder: (_) => const AlertDialog(content: Row(children: [CircularProgressIndicator(), SizedBox(width: 16), Text('피드백 생성 중...')])));
    try {
      final updated = await simulationService.getFeedback(_sim.id);
      if (mounted) {
        Navigator.pop(context);
        Navigator.push(context, MaterialPageRoute(
          builder: (_) => FeedbackScreen(simulation: updated, persona: widget.persona),
        ));
      }
    } catch (e) {
      if (mounted) {
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('피드백 실패: $e')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.persona.name),
        actions: [
          IconButton(icon: const Icon(Icons.save), onPressed: _savepoint, tooltip: '저장점'),
          IconButton(icon: const Icon(Icons.history), onPressed: _showSavepoints, tooltip: '저장점 목록'),
          IconButton(icon: const Icon(Icons.assessment), onPressed: _getFeedback, tooltip: '피드백'),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              controller: _scrollCtrl,
              padding: const EdgeInsets.all(16),
              itemCount: _sim.turns.length,
              itemBuilder: (ctx, i) {
                final turn = _sim.turns[i];
                final isUser = turn.role == 'user';
                return Align(
                  alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                  child: Container(
                    margin: const EdgeInsets.symmetric(vertical: 4),
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
                    decoration: BoxDecoration(
                      color: isUser ? Theme.of(context).colorScheme.primary : Colors.grey.shade200,
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Text(turn.content,
                      style: TextStyle(color: isUser ? Colors.white : Colors.black87)),
                  ),
                );
              },
            ),
          ),
          if (_sending)
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              child: Row(children: [
                SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)),
                SizedBox(width: 8),
                Text('답변 생성 중...', style: TextStyle(color: Colors.grey)),
              ]),
            ),
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(border: Border(top: BorderSide(color: Colors.grey.shade300))),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _msgCtrl,
                    decoration: const InputDecoration(hintText: '메시지 입력...', border: OutlineInputBorder(), contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8)),
                    maxLines: null,
                    textInputAction: TextInputAction.send,
                    onSubmitted: (_) => _send(),
                  ),
                ),
                const SizedBox(width: 8),
                IconButton(
                  onPressed: _sending ? null : _send,
                  icon: const Icon(Icons.send),
                  color: Theme.of(context).colorScheme.primary,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
