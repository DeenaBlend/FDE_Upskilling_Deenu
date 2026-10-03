"""Save articles to markdown files."""
from typing import List
from pathlib import Path
from datetime import datetime
from src.models.article import Article
from src.storage.base_storage import ArticleStorage

class MarkdownStorage(ArticleStorage):
    """
    Saves articles to markdown files.
    
    Single Responsibility: File storage only.
    """
    
    def __init__(self, base_path: str = "data/articles"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def save(self, articles: List[Article], filename: str = None) -> Path:
        """
        Save articles to markdown file.
        
        Args:
            articles: List of articles to save
            filename: Optional filename, auto-generated if not provided
            
        Returns:
            Path to saved file
        """
        if filename is None:
            # Auto-generate filename with timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
            filename = f"articles_{timestamp}.md"
        
        filepath = self.base_path / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            # Header
            f.write("# News Articles\n\n")
            f.write(
                f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            )
            f.write(f"**Total Articles:** {len(articles)}\n\n")
            f.write("---\n\n")
            
            for article in articles:
                f.write(article.to_markdown())
                f.write("\n---\n\n")
        
        print(f"💾 Saved {len(articles)} articles to: {filepath}")
        return filepath
