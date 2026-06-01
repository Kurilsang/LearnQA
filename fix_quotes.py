"""Fix Chinese quote issues in analyze_adaptive.py"""
import re

with open(r'd:\Develop\Projects\作业区\数据挖掘\自动刷课\analyze_adaptive.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace Chinese context ASCII double quotes with Unicode curly quotes
# Pattern: Chinese char + " + Chinese char → Chinese char + \u201c + Chinese char
# This is a best-effort fix for the specific patterns in this file

replacements = [
    # In print() and f-string statements
    ('包含"自适应练习"', '包含「自适应练习」'),
    ('点击"自适应练习"', '点击「自适应练习」'),
    ('查找"继续训练/开始训练/开始学习"按钮', '查找「继续训练/开始训练/开始学习」按钮'),
    ('查找"下一题"按钮', '查找「下一题」按钮'),
    ('查找"交卷/提交"按钮', '查找「交卷/提交」按钮'),
    ('包含"常见数据挖掘算法"', '包含「常见数据挖掘算法」'),
    ('点击包含"自适应练习"', '点击包含「自适应练习」'),
    ('查找包含"自适应练习"', '查找包含「自适应练习」'),
    ('未能点击"自适应练习"', '未能点击「自适应练习」'),
    ('类型为"自适应练习"', '类型为「自适应练习」'),
    ('包含"继续训练"等按钮', '包含「继续训练」等按钮'),
    ('列表中的"自适应练习"', '列表中的「自适应练习」'),
    # Comments
    ('可能包含"自适应练习"', '可能包含「自适应练习」'),
]

for old, new in replacements:
    content = content.replace(old, new)

with open(r'd:\Develop\Projects\作业区\数据挖掘\自动刷课\analyze_adaptive.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed quotes in analyze_adaptive.py")

# Verify no remaining issues
lines = content.split('\n')
issues = 0
for i, line in enumerate(lines, 1):
    if re.search(r'[\u4e00-\u9fff]"[\u4e00-\u9fff]', line):
        print(f'  STILL ISSUE Line {i}: {line[:100]}')
        issues += 1

if issues == 0:
    print("All issues resolved!")
