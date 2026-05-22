import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import '../../core/models/persona.dart';
import '../../core/api/persona_service.dart';
import '../../core/auth/auth_service.dart';
import 'persona_detail_screen.dart';

class PersonaListScreen extends StatefulWidget {
  final VoidCallback onLogout;

  const PersonaListScreen({super.key, required this.onLogout});

  @override
  State<PersonaListScreen> createState() => _PersonaListScreenState();
}

class _PersonaListScreenState extends State<PersonaListScreen> {
  List<Persona> _personas = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadPersonas();
  }

  Future<void> _loadPersonas() async {
    setState(() { _loading = true; _error = null; });
    try {
      final personas = await personaService.getPersonas();
      if (mounted) setState(() { _personas = personas; _loading = false; });
    } catch (e) {
      if (mounted) setState(() { _error = '불러오기 실패: $e'; _loading = false; });
    }
  }

  Future<void> _uploadFile() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['txt'],
    );
    if (result == null || result.files.single.path == null) return;

    final path = result.files.single.path!;
    if (!mounted) return;

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => const AlertDialog(content: Row(children: [CircularProgressIndicator(), SizedBox(width: 16), Text('분석 중...')]))
    );

    try {
      final newPersonas = await personaService.uploadKakaoTalk(path);
      if (mounted) {
        Navigator.pop(context);
        setState(() => _personas = [..._personas, ...newPersonas]);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('${newPersonas.length}명의 페르소나가 생성되었습니다.')),
        );
      }
    } catch (e) {
      if (mounted) {
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('업로드 실패: $e')));
      }
    }
  }

  Future<void> _logout() async {
    await authService.logout();
    widget.onLogout();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('내 페르소나'),
        actions: [
          IconButton(icon: const Icon(Icons.logout), onPressed: _logout),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                  Text(_error!), const SizedBox(height: 16),
                  ElevatedButton(onPressed: _loadPersonas, child: const Text('재시도')),
                ]))
              : _personas.isEmpty
                  ? Center(child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                      const Icon(Icons.person_add, size: 64, color: Colors.grey),
                      const SizedBox(height: 16),
                      const Text('카카오톡 대화 파일을 업로드하여\n첫 페르소나를 만들어보세요', textAlign: TextAlign.center),
                      const SizedBox(height: 24),
                      ElevatedButton.icon(
                        onPressed: _uploadFile,
                        icon: const Icon(Icons.upload_file),
                        label: const Text('파일 업로드'),
                      ),
                    ]))
                  : RefreshIndicator(
                      onRefresh: _loadPersonas,
                      child: ListView.builder(
                        padding: const EdgeInsets.all(16),
                        itemCount: _personas.length,
                        itemBuilder: (ctx, i) {
                          final p = _personas[i];
                          return Card(
                            child: ListTile(
                              leading: CircleAvatar(child: Text(p.name[0])),
                              title: Text(p.name),
                              subtitle: Text(p.profileJson['summary'] as String? ?? ''),
                              trailing: const Icon(Icons.chevron_right),
                              onTap: () => Navigator.push(
                                context,
                                MaterialPageRoute(builder: (_) => PersonaDetailScreen(personaId: p.id)),
                              ).then((_) => _loadPersonas()),
                            ),
                          );
                        },
                      ),
                    ),
      floatingActionButton: _personas.isNotEmpty
          ? FloatingActionButton(
              onPressed: _uploadFile,
              child: const Icon(Icons.add),
            )
          : null,
    );
  }
}
