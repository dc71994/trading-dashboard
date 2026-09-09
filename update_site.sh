#!/bin/bash

# Navigate to the project directory
cd "$(dirname "$0")"

echo "🔄 Running RS System Scanner..."
python3 -m rs_system.main

echo "📦 Committing changes to Git..."
git add .
git commit -m "Automated update: $(date '+%Y-%m-%d %H:%M:%S')"

echo "🚀 Pushing to GitHub..."
git push origin main

echo "✅ Deployment complete! Your website will update in a minute or two."
