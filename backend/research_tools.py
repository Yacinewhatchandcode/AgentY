"""
AgentY Research Tools
Web search and GitHub code search for intelligent agents.
"""
import os
import json
import urllib.request
import urllib.parse
from typing import List, Dict, Optional
from datetime import datetime


class WebSearchTool:
    """
    Web search using Perplexity API via MCP or direct API calls.
    """
    
    def __init__(self):
        self.api_key = os.environ.get("PERPLEXITY_API_KEY", "")
        self.base_url = "https://api.perplexity.ai/chat/completions"
    
    async def search(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Search the web for information.
        Returns structured results with sources.
        """
        if not self.api_key:
            return [{
                "title": "API Key Missing",
                "content": "Set PERPLEXITY_API_KEY environment variable",
                "source": "system"
            }]
        
        try:
            data = json.dumps({
                "model": "llama-3.1-sonar-small-128k-online",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a research assistant. Provide factual, well-sourced answers."
                    },
                    {
                        "role": "user",
                        "content": f"Search and summarize: {query}"
                    }
                ],
                "max_tokens": 1000
            }).encode('utf-8')
            
            req = urllib.request.Request(
                self.base_url,
                data=data,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                citations = result.get("citations", [])
                
                return [{
                    "title": f"Search: {query[:50]}",
                    "content": content,
                    "sources": citations,
                    "timestamp": datetime.now().isoformat()
                }]
        
        except Exception as e:
            return [{
                "title": "Search Error",
                "content": str(e),
                "source": "error"
            }]
    
    def search_sync(self, query: str) -> List[Dict]:
        """Synchronous version of search."""
        import asyncio
        return asyncio.get_event_loop().run_until_complete(self.search(query))


class GitHubSearchTool:
    """
    Search GitHub for code examples and repositories.
    """
    
    def __init__(self):
        self.api_token = os.environ.get("GITHUB_TOKEN", "")
        self.base_url = "https://api.github.com"
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Dict:
        """Make a request to GitHub API."""
        url = f"{self.base_url}/{endpoint}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AgentY-Bot"
        }
        
        if self.api_token:
            headers["Authorization"] = f"token {self.api_token}"
        
        req = urllib.request.Request(url, headers=headers)
        
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            return {"error": str(e)}
    
    def search_code(
        self,
        query: str,
        language: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict]:
        """
        Search GitHub for code matching the query.
        """
        search_query = query
        if language:
            search_query += f" language:{language}"
        
        result = self._make_request("search/code", {
            "q": search_query,
            "per_page": limit
        })
        
        if "error" in result:
            return [{"error": result["error"]}]
        
        items = result.get("items", [])
        return [{
            "name": item.get("name"),
            "path": item.get("path"),
            "repo": item.get("repository", {}).get("full_name"),
            "url": item.get("html_url"),
            "score": item.get("score", 0)
        } for item in items[:limit]]
    
    def search_repos(
        self,
        query: str,
        language: Optional[str] = None,
        sort: str = "stars",
        limit: int = 5
    ) -> List[Dict]:
        """
        Search GitHub for repositories.
        """
        search_query = query
        if language:
            search_query += f" language:{language}"
        
        result = self._make_request("search/repositories", {
            "q": search_query,
            "sort": sort,
            "order": "desc",
            "per_page": limit
        })
        
        if "error" in result:
            return [{"error": result["error"]}]
        
        items = result.get("items", [])
        return [{
            "name": item.get("full_name"),
            "description": item.get("description", "")[:200],
            "url": item.get("html_url"),
            "stars": item.get("stargazers_count", 0),
            "language": item.get("language"),
            "topics": item.get("topics", [])[:5]
        } for item in items[:limit]]
    
    def get_file_content(self, owner: str, repo: str, path: str) -> str:
        """Get the content of a file from a repository."""
        result = self._make_request(f"repos/{owner}/{repo}/contents/{path}")
        
        if "error" in result:
            return f"Error: {result['error']}"
        
        content = result.get("content", "")
        if content:
            import base64
            try:
                return base64.b64decode(content).decode('utf-8')
            except:
                return "Error: Could not decode file content"
        
        return "No content found"
    
    def find_similar_implementations(
        self,
        description: str,
        language: str = "python",
        limit: int = 3
    ) -> List[Dict]:
        """
        Find similar implementations on GitHub.
        Useful for agents to learn from existing code.
        """
        # Search for repos
        repos = self.search_repos(description, language=language, limit=limit)
        
        results = []
        for repo in repos:
            if "error" not in repo:
                results.append({
                    "type": "repository",
                    "name": repo["name"],
                    "description": repo["description"],
                    "url": repo["url"],
                    "stars": repo["stars"],
                    "relevance": "Similar project found"
                })
        
        # Search for code snippets
        code = self.search_code(description, language=language, limit=limit)
        
        for c in code:
            if "error" not in c:
                results.append({
                    "type": "code",
                    "name": c["name"],
                    "path": c["path"],
                    "repo": c["repo"],
                    "url": c["url"],
                    "relevance": "Similar code found"
                })
        
        return results


# Tool instances
web_search = WebSearchTool()
github_search = GitHubSearchTool()


def search_for_solution(error: str, language: str = "python") -> Dict:
    """
    Combined search for error solutions.
    Searches both web and GitHub for solutions.
    """
    results = {
        "error": error[:100],
        "web_results": [],
        "github_results": [],
        "timestamp": datetime.now().isoformat()
    }
    
    # Search web for error solution
    try:
        web_results = web_search.search_sync(f"how to fix {error}")
        results["web_results"] = web_results
    except:
        pass
    
    # Search GitHub for similar code/fixes
    try:
        github_results = github_search.search_code(
            f"{error} fix",
            language=language,
            limit=3
        )
        results["github_results"] = github_results
    except:
        pass
    
    return results
