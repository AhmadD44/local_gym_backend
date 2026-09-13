from pathlib import Path

root = Path('C:/Users/ahmad/Desktop/Gym_App/gym_app')
tags = {
    'lib/features/trainers/presentation/screens/trainer_programs_screen.dart': 'trainer-new-program',
    'lib/features/chat/presentation/screens/conversations_screen.dart': 'chat-new-conversation',
    'lib/features/exercises/presentation/screens/exercises_screen.dart': 'exercise-create',
}
for relative, tag in tags.items():
    path = root / relative
    text = path.read_text(encoding='utf-8')
    if f"heroTag: '{tag}'" in text:
        continue
    import re
    text, count = re.subn(r'(FloatingActionButton(?:\.extended)?\(\n)(\s+)(onPressed:)',
                         lambda m: f"{m[1]}{m[2]}heroTag: '{tag}',\n{m[2]}{m[3]}", text)
    assert count == 1, relative
    path.write_text(text, encoding='utf-8', newline='\n')

path = root / 'lib/features/navigation/app_shell.dart'
text = path.read_text(encoding='utf-8')
old = '''                  child: _builtIndices.contains(index)
                      ? _DestinationPage(
                          destination: destination,
                          role: widget.role,
                        )
                      : const SizedBox.shrink(),'''
new = '''                  // Retained tabs must not participate in route Hero flights.
                  child: HeroMode(
                    enabled: index == _selectedIndex,
                    child: _builtIndices.contains(index)
                        ? _DestinationPage(
                            destination: destination,
                            role: widget.role,
                          )
                        : const SizedBox.shrink(),
                  ),'''
assert old in text
path.write_text(text.replace(old, new), encoding='utf-8', newline='\n')
