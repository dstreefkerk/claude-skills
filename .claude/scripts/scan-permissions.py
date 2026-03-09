#!/usr/bin/env python3
"""Scan all project settings.local.json files to find Bash permission patterns
not covered by the Universal Base presets."""

import json
import glob
import re
from collections import Counter
from pathlib import Path

# Patterns already in presets (extracted from permission-presets.md)
COVERED_COMMANDS = {
    # Universal Base
    'cd', 'ls', 'pwd', 'cat', 'head', 'tail', 'less', 'more', 'wc', 'sort',
    'mkdir', 'mktemp', 'rm', 'rmdir', 'cp', 'mv', 'ln', 'touch', 'chmod',
    'chown', 'find', 'tree', 'du', 'df', 'readlink', 'realpath', 'stat', 'file',
    'tar', 'zip', 'unzip', 'gzip', 'gunzip',
    'grep', 'rg', 'awk', 'sed', 'diff', 'jq', 'yq', 'echo', 'printf', 'tee',
    'cut', 'paste', 'tr', 'uniq', 'xargs', 'basename', 'dirname',
    'which', 'whereis', 'type', 'ps', 'kill', 'env', 'export', 'unset',
    'source', 'bash', 'sh', 'date', 'uname', 'make', 'cmake', 'id', 'whoami',
    'hostname', 'uptime',
    'pkill', 'killall', 'lsof', 'pgrep', 'timeout', 'sleep', 'wait', 'time',
    'nohup', 'ss', 'top', 'htop', 'free', 'screen', 'tmux',
    'openssl', 'ssh-keygen', 'gitleaks', 'md5sum', 'shasum',
    'printenv', 'xxd', 'base64', 'nslookup', 'seq', 'bc', 'column', 'iconv',
    'strings', 'patch', 'cmp',
    'curl', 'wget', 'ssh', 'scp', 'rsync', 'dig', 'ping',
    'python3', 'python',
    'git', 'gh',
    # JS/TS
    'node', 'npm', 'npx', 'pnpm', 'yarn', 'nvm', 'fnm', 'volta',
    'tsc', 'tsx', 'ts-node', 'esbuild', 'vite', 'turbo', 'pm2',
    'jest', 'vitest', 'playwright', 'playwright-cli', 'cypress',
    'eslint', 'prettier', 'biome',
    'corepack', 'tsup', 'swc', 'rollup', 'webpack', 'nx', 'lerna', 'changeset',
    'storybook', 'bun', 'bunx', 'deno',
    # Python
    'pip', 'pip3', 'uv', 'poetry', 'pipx', 'conda',
    'pytest', 'mypy', 'ruff', 'black', 'flake8', 'isort',
    'flask', 'uvicorn', 'gunicorn', 'django-admin', 'jupyter',
    'pdm', 'hatch', 'pre-commit',
    # PHP
    'php', 'composer', 'wp', 'phpunit', 'phpstan', 'phpcs', 'phpcbf', 'pest',
    'artisan', 'sail',
    # Go, Rust, Ruby
    'go', 'golangci-lint', 'cargo', 'rustc', 'rustup',
    'ruby', 'gem', 'bundle', 'bundler', 'rails', 'rake', 'rspec',
    # Cloudflare, Vercel, Docker
    'wrangler', 'miniflare', 'vercel', 'prisma',
    'docker', 'docker-compose', 'kubectl', 'helm', 'terraform', 'pulumi',
    # Database
    'psql', 'mysql', 'sqlite3', 'redis-cli', 'mongosh',
    'pg_dump', 'pg_restore', 'createdb', 'dropdb', 'mysqldump', 'turso', 'pscale',
    # Cloud
    'aws', 'gcloud', 'gsutil', 'az', 'firebase',
    # AI/GPU
    'ollama', 'nvidia-smi',
    # macOS
    'brew', 'open', 'pbcopy', 'pbpaste', 'sips', 'screencapture', 'osascript',
    'caffeinate', 'defaults', 'mdfind', 'mdls', 'ditto', 'say', 'plutil',
    'softwareupdate', 'xcode-select', 'xattr',
    # LLM CLIs
    'claude', 'gemini-coach', 'elevenlabs', 'fastmcp',
    # Media
    'convert', 'identify', 'exiftool', 'ffmpeg', 'ffprobe', 'ffplay', 'magick',
    # New presets
    'java', 'javac', 'jar', 'mvn', 'gradle', 'gradlew', 'kotlin', 'kotlinc',
    'sbt', 'scala', 'dotnet', 'nuget', 'elixir', 'mix', 'iex', 'swift', 'swiftc',
    'astro', 'hugo', 'gatsby', 'eleventy', 'jekyll',
    'railway', 'fly', 'flyctl', 'netlify', 'supabase', 'heroku', 'render', 'cpanel',
    'ngrok', 'cloudflared', 'mkcert', 'certbot',
    'stripe', 'twilio', 'auth0', 'sentry-cli',
    'pandoc', 'wkhtmltopdf',
    'act', 'code', 'cursor', 'zed', 'vim', 'nvim',
    # Linux
    'systemctl', 'journalctl', 'crontab', 'sudo', 'apt', 'apt-get', 'dpkg', 'yum', 'dnf',
    # Mobile
    'eas', 'adb', 'react-native', 'flutter', 'dart', 'xcodebuild', 'pod', 'xcrun', 'fastlane',
}

# Extract first command word from a Bash permission pattern
def extract_command(perm):
    m = re.match(r'Bash\(([a-zA-Z0-9_./-]+)', perm)
    if m:
        cmd = m.group(1)
        # Skip paths, env vars, shell constructs
        if cmd.startswith('/') or cmd.startswith('./') or cmd.startswith('~'):
            return f"[path:{cmd}]"
        if cmd in ('do', 'done', 'for', 'while', 'if', 'then', 'else', 'fi',
                   'elif', 'case', 'esac', 'in', 'true', 'false', 'break',
                   'continue', 'return', 'test', '['):
            return None  # Shell constructs
        if '=' in cmd or cmd.startswith('__NEW_LINE'):
            return None  # Env vars or artifacts
        return cmd
    return None

# Scan all settings files
settings_files = glob.glob('/Users/jez/Documents/*/.claude/settings.local.json')
settings_files += glob.glob('/Users/jez/Documents/*/*/.claude/settings.local.json')

uncovered = Counter()
webfetch_domains = Counter()
all_commands = Counter()

for sf in settings_files:
    try:
        data = json.loads(Path(sf).read_text())
        perms = data.get('permissions', {}).get('allow', [])
        for p in perms:
            if p.startswith('Bash('):
                cmd = extract_command(p)
                if cmd and not cmd.startswith('[path:'):
                    all_commands[cmd] += 1
                    if cmd not in COVERED_COMMANDS:
                        uncovered[cmd] += 1
            elif p.startswith('WebFetch(domain:'):
                domain = p.replace('WebFetch(domain:', '').rstrip(')')
                webfetch_domains[domain] += 1
    except (json.JSONDecodeError, FileNotFoundError):
        continue

print("=== UNCOVERED BASH COMMANDS (by frequency) ===")
print(f"{'Command':<30} {'Count':>5}  Notes")
print("-" * 60)
for cmd, count in uncovered.most_common(50):
    print(f"{cmd:<30} {count:>5}")

print(f"\n=== TOP WEBFETCH DOMAINS (not blanket) ===")
for domain, count in webfetch_domains.most_common(30):
    print(f"  {domain:<45} {count:>3}")

print(f"\n=== STATS ===")
print(f"Total settings files scanned: {len(settings_files)}")
print(f"Unique commands found: {len(all_commands)}")
print(f"Already covered by presets: {len(all_commands) - len(uncovered)}")
print(f"Not in presets: {len(uncovered)}")
