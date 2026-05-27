name: WeatherWorld Hourly Recorder

on:
  schedule:
    - cron: '0 * * * *'   # runs every hour
  workflow_dispatch:        # lets you trigger it manually too

jobs:
  record:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Run weather recorder
        run: python weather_recorder.py

      - name: Save data to repo
        run: |
          git config user.email "weatherbot@auto.com"
          git config user.name  "WeatherBot"
          git add weather_data/
          git diff --cached --quiet || git commit -m "data: $(date -u +'%Y-%m-%d %H:%M')"
          git push