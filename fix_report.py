import re

with open('rs_system/report.py', 'r') as f:
    code = f.read()

# Fix filterBasing JS logic
# old: if (pctFromHigh >= maxDepth && pctFromHigh <= 0) {
# new: if (pctFromHigh >= maxDepth) {
code = code.replace("if (pctFromHigh >= maxDepth && pctFromHigh <= 0) {", "if (pctFromHigh >= maxDepth) {")

with open('rs_system/report.py', 'w') as f:
    f.write(code)
print("Fixed filterBasing JS logic.")
