import ast

code = open('distance_test.py', encoding='utf-8').read()
ast.parse(code)
print('Lines          :', len(code.splitlines()), flush=True)
print('win32com used  :', 'win32com' in code, flush=True)
print('pyttsx3 used   :', 'pyttsx3' in code, flush=True)
print('CoInitialize   :', 'CoInitialize' in code, flush=True)
print('Inference thread:', 'inference_worker' in code, flush=True)
print('Speech thread  :', 'speech_worker' in code or '_worker' in code, flush=True)
print('Syntax         : OK', flush=True)
