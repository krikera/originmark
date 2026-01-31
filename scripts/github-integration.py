#!/usr/bin/env python3
"""
OriginMark GitHub Integration Script

This script provides local GitHub integration for signing commits and repositories.
It can be used as a pre-commit hook or run manually to sign repository contents.
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from typing import List, Dict, Optional
import requests

class GitHubOriginMark:
    def __init__(self, api_url: str = "http://localhost:8000", api_key: Optional[str] = None):
        self.api_url = api_url
        self.api_key = api_key or os.getenv('ORIGINMARK_API_KEY')
        self.repo_root = self.find_git_root()
        
    def find_git_root(self) -> Path:
        """Find the root of the git repository"""
        current = Path.cwd()
        while current != current.parent:
            if (current / '.git').exists():
                return current
            current = current.parent
        raise RuntimeError("Not in a git repository")
    
    def get_git_info(self) -> Dict[str, str]:
        """Get current git information"""
        try:
            # Get current commit hash
            commit_hash = subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'], 
                cwd=self.repo_root,
                text=True
            ).strip()
            
            # Get current branch
            branch = subprocess.check_output(
                ['git', 'branch', '--show-current'], 
                cwd=self.repo_root,
                text=True
            ).strip()
            
            # Get author info
            author_name = subprocess.check_output(
                ['git', 'config', 'user.name'], 
                cwd=self.repo_root,
                text=True
            ).strip()
            
            author_email = subprocess.check_output(
                ['git', 'config', 'user.email'], 
                cwd=self.repo_root,
                text=True
            ).strip()
            
            # Get remote origin URL
            try:
                remote_url = subprocess.check_output(
                    ['git', 'config', '--get', 'remote.origin.url'], 
                    cwd=self.repo_root,
                    text=True
                ).strip()
            except subprocess.CalledProcessError:
                remote_url = "local"
            
            return {
                'commit_hash': commit_hash,
                'branch': branch,
                'author_name': author_name,
                'author_email': author_email,
                'remote_url': remote_url
            }
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get git info: {e}")
    
    def get_changed_files(self, commit_range: Optional[str] = None) -> List[Path]:
        """Get list of changed files in git"""
        try:
            if commit_range:
                cmd = ['git', 'diff', '--name-only', commit_range]
            else:
                # Get files in the last commit
                cmd = ['git', 'diff', '--name-only', 'HEAD~1', 'HEAD']
            
            output = subprocess.check_output(
                cmd, 
                cwd=self.repo_root,
                text=True
            ).strip()
            
            if not output:
                return []
            
            files = []
            for file_path in output.split('\n'):
                full_path = self.repo_root / file_path
                if full_path.exists() and full_path.is_file():
                    files.append(full_path)
            
            return files
        except subprocess.CalledProcessError:
            return []
    
    def should_sign_file(self, file_path: Path) -> bool:
        """Determine if a file should be signed"""
        # File types to sign
        signable_extensions = {
            '.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.rs', '.java', 
            '.cpp', '.c', '.h', '.hpp', '.cs', '.rb', '.php', '.swift',
            '.kt', '.scala', '.clj', '.hs', '.ml', '.elm', '.dart',
            '.md', '.txt', '.yml', '.yaml', '.json', '.toml', '.ini'
        }
        
        # Skip certain directories
        skip_dirs = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'dist', 'build'}
        
        # Check if file is in skipped directory
        for part in file_path.parts:
            if part in skip_dirs:
                return False
        
        # Check file extension
        return file_path.suffix.lower() in signable_extensions
    
    def sign_file_local(self, file_path: Path, git_info: Dict[str, str]) -> bool:
        """Sign a file using local OriginMark CLI"""
        try:
            cmd = [
                'originmark', 'sign', str(file_path),
                '--author', f"{git_info['author_name']} <{git_info['author_email']}>",
                '--model', f"Git Commit {git_info['commit_hash'][:8]}"
            ]
            
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to sign {file_path}: {e}")
            return False
    
    def sign_file_api(self, file_path: Path, git_info: Dict[str, str]) -> bool:
        """Sign a file using OriginMark API"""
        if not self.api_key:
            raise RuntimeError("API key required for API signing")
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                data = {
                    'author': f"{git_info['author_name']} <{git_info['author_email']}>",
                    'model_used': f"Git Commit {git_info['commit_hash'][:8]}"
                }
                headers = {'Authorization': f'Bearer {self.api_key}'}
                
                response = requests.post(
                    f"{self.api_url}/sign",
                    files=files,
                    data=data,
                    headers=headers
                )
                response.raise_for_status()
                
                # Save signature to sidecar file
                signature_data = response.json()
                sidecar_path = file_path.with_suffix(file_path.suffix + '.originmark.json')
                with open(sidecar_path, 'w') as f:
                    json.dump(signature_data, f, indent=2)
                
                return True
        except Exception as e:
            print(f"Failed to sign {file_path} via API: {e}")
            return False
    
    def sign_files(self, files: List[Path], use_api: bool = False) -> Dict[str, int]:
        """Sign multiple files"""
        git_info = self.get_git_info()
        
        stats = {'signed': 0, 'failed': 0, 'skipped': 0}
        
        for file_path in files:
            if not self.should_sign_file(file_path):
                stats['skipped'] += 1
                continue
            
            print(f"Signing: {file_path.relative_to(self.repo_root)}")
            
            if use_api:
                success = self.sign_file_api(file_path, git_info)
            else:
                success = self.sign_file_local(file_path, git_info)
            
            if success:
                stats['signed'] += 1
            else:
                stats['failed'] += 1
        
        return stats
    
    def verify_repository(self) -> Dict[str, int]:
        """Verify all signatures in the repository"""
        signature_files = list(self.repo_root.rglob('*.originmark.json'))
        
        stats = {'verified': 0, 'failed': 0}
        
        for sig_file in signature_files:
            original_file = sig_file.with_suffix('').with_suffix(
                sig_file.suffix.replace('.originmark.json', '')
            )
            
            if not original_file.exists():
                print(f"Warning: Original file not found for {sig_file}")
                continue
            
            try:
                cmd = ['originmark', 'verify', str(original_file)]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    stats['verified'] += 1
                    print(f"✓ Verified: {original_file.relative_to(self.repo_root)}")
                else:
                    stats['failed'] += 1
                    print(f"✗ Failed: {original_file.relative_to(self.repo_root)}")
                    
            except subprocess.CalledProcessError:
                stats['failed'] += 1
                print(f"✗ Error verifying: {original_file.relative_to(self.repo_root)}")
        
        return stats
    
    def create_signature_manifest(self) -> Path:
        """Create a manifest of all signatures in the repository"""
        git_info = self.get_git_info()
        signature_files = list(self.repo_root.rglob('*.originmark.json'))
        
        manifest = {
            'repository': {
                'url': git_info['remote_url'],
                'commit': git_info['commit_hash'],
                'branch': git_info['branch'],
                'author': f"{git_info['author_name']} <{git_info['author_email']}>"
            },
            'generated_at': subprocess.check_output(['date', '-Iseconds'], text=True).strip(),
            'signatures': []
        }
        
        for sig_file in signature_files:
            try:
                with open(sig_file) as f:
                    sig_data = json.load(f)
                
                original_file = sig_file.with_suffix('').with_suffix(
                    sig_file.suffix.replace('.originmark.json', '')
                )
                
                manifest['signatures'].append({
                    'file': str(original_file.relative_to(self.repo_root)),
                    'signature_id': sig_data.get('id'),
                    'content_hash': sig_data.get('content_hash'),
                    'timestamp': sig_data.get('timestamp'),
                    'author': sig_data.get('metadata', {}).get('author')
                })
                
            except Exception as e:
                print(f"Warning: Could not process {sig_file}: {e}")
        
        manifest_path = self.repo_root / 'originmark-manifest.json'
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return manifest_path

def main():
    parser = argparse.ArgumentParser(description='OriginMark GitHub Integration')
    parser.add_argument('--api-url', default='http://localhost:8000', help='OriginMark API URL')
    parser.add_argument('--api-key', help='OriginMark API key (or set ORIGINMARK_API_KEY env var)')
    parser.add_argument('--use-api', action='store_true', help='Use API instead of local CLI')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Sign command
    sign_parser = subparsers.add_parser('sign', help='Sign files')
    sign_parser.add_argument('files', nargs='*', help='Files to sign (default: changed files)')
    sign_parser.add_argument('--all', action='store_true', help='Sign all signable files')
    sign_parser.add_argument('--commit-range', help='Sign files changed in commit range')
    
    # Verify command
    verify_parser = subparsers.add_parser('verify', help='Verify repository signatures')
    
    # Manifest command
    manifest_parser = subparsers.add_parser('manifest', help='Create signature manifest')
    
    # Pre-commit hook command
    hook_parser = subparsers.add_parser('pre-commit', help='Run as pre-commit hook')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    github_om = GitHubOriginMark(api_url=args.api_url, api_key=args.api_key)
    
    if args.command == 'sign':
        if args.files:
            files = [Path(f) for f in args.files]
        elif args.all:
            files = [f for f in github_om.repo_root.rglob('*') 
                    if f.is_file() and github_om.should_sign_file(f)]
        else:
            files = github_om.get_changed_files(args.commit_range)
        
        if not files:
            print("No files to sign")
            return
        
        stats = github_om.sign_files(files, use_api=args.use_api)
        print(f"\nSigning complete: {stats['signed']} signed, {stats['failed']} failed, {stats['skipped']} skipped")
        
    elif args.command == 'verify':
        stats = github_om.verify_repository()
        print(f"\nVerification complete: {stats['verified']} verified, {stats['failed']} failed")
        
        if stats['failed'] > 0:
            sys.exit(1)
        
    elif args.command == 'manifest':
        manifest_path = github_om.create_signature_manifest()
        print(f"Signature manifest created: {manifest_path}")
        
    elif args.command == 'pre-commit':
        # Sign only staged files
        try:
            staged_files = subprocess.check_output(
                ['git', 'diff', '--cached', '--name-only'], 
                cwd=github_om.repo_root,
                text=True
            ).strip().split('\n')
            
            files = []
            for file_path in staged_files:
                if file_path:  # Skip empty strings
                    full_path = github_om.repo_root / file_path
                    if full_path.exists() and full_path.is_file():
                        files.append(full_path)
            
            if files:
                stats = github_om.sign_files(files, use_api=args.use_api)
                print(f"Pre-commit signing: {stats['signed']} signed, {stats['failed']} failed")
                
                # Stage the signature files
                for file_path in files:
                    sidecar = file_path.with_suffix(file_path.suffix + '.originmark.json')
                    if sidecar.exists():
                        subprocess.run(['git', 'add', str(sidecar)], cwd=github_om.repo_root)
            else:
                print("No staged files to sign")
                
        except subprocess.CalledProcessError as e:
            print(f"Failed to get staged files: {e}")
            sys.exit(1)

if __name__ == '__main__':
    main() 