# ============================================================================
# Prométhée — Assistant IA desktop
# ============================================================================
# Auteur  : Pierre COUGET
# Licence : GNU Affero General Public License v3.0 (AGPL-3.0)
#           https://www.gnu.org/licenses/agpl-3.0.html
# Année   : 2026
# ----------------------------------------------------------------------------
# Ce fichier fait partie du projet Prométhée.
# Vous pouvez le redistribuer et/ou le modifier selon les termes de la
# licence AGPL-3.0 publiée par la Free Software Foundation.
# ============================================================================

"""
url_extractor.py — Extraction intelligente du contenu d'articles web
Distingue le contenu principal (article) du contenu de navigation
"""
from typing import Optional, Dict
import re


def is_available() -> bool:
    """Vérifie si les dépendances sont disponibles."""
    try:
        import requests
        from bs4 import BeautifulSoup
        return True
    except ImportError:
        return False


def extract_article_content(url: str, timeout: int = 10) -> Dict[str, any]:
    """
    Extrait intelligemment le contenu principal d'une URL (article vs navigation).
    
    Args:
        url: URL à extraire
        timeout: Timeout en secondes
    
    Returns:
        Dict avec 'success', 'title', 'content', 'author', 'date', 'description', 'error'
    """
    if not is_available():
        return {
            'success': False,
            'error': 'requests et beautifulsoup4 non installés'
        }
    
    try:
        import requests
        from bs4 import BeautifulSoup
        from datetime import datetime
        
        # Headers pour éviter les blocages
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Requête
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        # Parser HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extraire les métadonnées
        title = _extract_title(soup)
        author = _extract_author(soup)
        date = _extract_date(soup)
        description = _extract_description(soup)
        
        # Extraire le contenu principal (article)
        article_content = _extract_main_content(soup)
        
        # Nettoyer le contenu
        cleaned_content = _clean_text(article_content)
        
        # Statistiques
        word_count = len(cleaned_content.split())
        char_count = len(cleaned_content)
        
        return {
            'success': True,
            'url': url,
            'title': title,
            'author': author,
            'date': date,
            'description': description,
            'content': cleaned_content,
            'word_count': word_count,
            'char_count': char_count,
            'error': None
        }
    
    except requests.exceptions.Timeout:
        return {'success': False, 'error': 'Timeout lors de la requête'}
    
    except requests.exceptions.RequestException as e:
        return {'success': False, 'error': f'Erreur réseau : {str(e)[:60]}'}
    
    except Exception as e:
        return {'success': False, 'error': f'Erreur : {str(e)[:60]}'}


def _extract_title(soup) -> str:
    """Extrait le titre de l'article."""
    # Ordre de priorité pour le titre
    
    # 1. Open Graph
    og_title = soup.find('meta', property='og:title')
    if og_title and og_title.get('content'):
        return og_title['content'].strip()
    
    # 2. Twitter Card
    twitter_title = soup.find('meta', {'name': 'twitter:title'})
    if twitter_title and twitter_title.get('content'):
        return twitter_title['content'].strip()
    
    # 3. Balise <title>
    title_tag = soup.find('title')
    if title_tag:
        title = title_tag.string.strip()
        # Nettoyer (souvent "Titre | Site Name")
        if '|' in title:
            title = title.split('|')[0].strip()
        if '-' in title and len(title.split('-')) > 1:
            title = title.split('-')[0].strip()
        return title
    
    # 4. Premier <h1>
    h1 = soup.find('h1')
    if h1:
        return h1.get_text().strip()
    
    return "Sans titre"


def _extract_author(soup) -> Optional[str]:
    """Extrait l'auteur de l'article."""
    # Open Graph
    og_author = soup.find('meta', property='article:author')
    if og_author and og_author.get('content'):
        return og_author['content'].strip()
    
    # Balise meta author
    meta_author = soup.find('meta', {'name': 'author'})
    if meta_author and meta_author.get('content'):
        return meta_author['content'].strip()
    
    # Chercher dans le contenu
    author_patterns = [
        {'class': re.compile(r'author', re.I)},
        {'rel': 'author'},
        {'itemprop': 'author'}
    ]
    
    for pattern in author_patterns:
        author_elem = soup.find(['span', 'div', 'p', 'a'], pattern)
        if author_elem:
            return author_elem.get_text().strip()
    
    return None


def _extract_date(soup) -> Optional[str]:
    """Extrait la date de publication."""
    # Open Graph
    og_date = soup.find('meta', property='article:published_time')
    if og_date and og_date.get('content'):
        return og_date['content'].strip()
    
    # Schema.org
    date_elem = soup.find(['time', 'span'], {'itemprop': 'datePublished'})
    if date_elem:
        return date_elem.get('datetime') or date_elem.get_text().strip()
    
    # Balise <time>
    time_elem = soup.find('time')
    if time_elem:
        return time_elem.get('datetime') or time_elem.get_text().strip()
    
    return None


def _extract_description(soup) -> Optional[str]:
    """Extrait la description de l'article."""
    # Open Graph
    og_desc = soup.find('meta', property='og:description')
    if og_desc and og_desc.get('content'):
        return og_desc['content'].strip()
    
    # Meta description
    meta_desc = soup.find('meta', {'name': 'description'})
    if meta_desc and meta_desc.get('content'):
        return meta_desc['content'].strip()
    
    return None


def _extract_main_content(soup) -> str:
    """
    Extrait le contenu principal (article) en ignorant la navigation.
    Utilise plusieurs heuristiques pour identifier le contenu pertinent.
    """
    # Supprimer les éléments de navigation
    for tag in soup(['nav', 'header', 'footer', 'aside', 'script', 'style', 
                     'iframe', 'noscript', 'form']):
        tag.decompose()
    
    # Supprimer les éléments avec classes/ids de navigation
    nav_patterns = [
        'nav', 'menu', 'sidebar', 'footer', 'header', 'advertisement',
        'ad', 'social', 'share', 'comment', 'related', 'recommend'
    ]
    
    for pattern in nav_patterns:
        for elem in soup.find_all(class_=re.compile(pattern, re.I)):
            elem.decompose()
        for elem in soup.find_all(id=re.compile(pattern, re.I)):
            elem.decompose()
    
    # Chercher le contenu principal par ordre de priorité
    
    # 1. Balises sémantiques HTML5
    article = soup.find('article')
    if article:
        return article.get_text()
    
    main = soup.find('main')
    if main:
        return main.get_text()
    
    # 2. Classes/IDs communes pour les articles
    content_patterns = [
        'article', 'post', 'entry', 'content', 'story', 'text',
        'body', 'main', 'blog', 'news'
    ]
    
    for pattern in content_patterns:
        # Chercher par classe
        elem = soup.find(['div', 'section'], class_=re.compile(pattern, re.I))
        if elem:
            return elem.get_text()
        
        # Chercher par ID
        elem = soup.find(['div', 'section'], id=re.compile(pattern, re.I))
        if elem:
            return elem.get_text()
    
    # 3. Heuristique : la div avec le plus de <p>
    divs = soup.find_all(['div', 'section'])
    best_div = None
    max_p_count = 0
    
    for div in divs:
        p_count = len(div.find_all('p'))
        # Ignorer les divs trop petites ou avec peu de texte
        text_length = len(div.get_text().strip())
        if p_count > max_p_count and text_length > 200:
            max_p_count = p_count
            best_div = div
    
    if best_div:
        return best_div.get_text()
    
    # 4. Fallback : tous les <p>
    paragraphs = soup.find_all('p')
    return '\n\n'.join([p.get_text() for p in paragraphs])


def _clean_text(text: str) -> str:
    """Nettoie le texte extrait."""
    if not text:
        return ""
    
    # Supprimer les espaces multiples
    text = re.sub(r'\s+', ' ', text)
    
    # Supprimer les lignes vides multiples
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if line:
            cleaned_lines.append(line)
    
    text = '\n'.join(cleaned_lines)
    
    # Limiter la taille
    if len(text) > 50000:
        text = text[:50000] + "\n\n[... contenu tronqué]"
    
    return text.strip()


def get_content_summary(content: Dict[str, any]) -> str:
    """
    Génère un résumé formaté du contenu extrait.
    
    Args:
        content: Dict retourné par extract_article_content
    
    Returns:
        Résumé formaté en texte
    """
    if not content.get('success'):
        return f"Erreur : {content.get('error', 'Inconnue')}"
    
    summary_parts = []
    
    # Titre
    if content.get('title'):
        summary_parts.append(f"# {content['title']}\n")
    
    # Métadonnées
    meta = []
    if content.get('author'):
        meta.append(f"**Auteur** : {content['author']}")
    if content.get('date'):
        meta.append(f"**Date** : {content['date']}")
    if content.get('word_count'):
        meta.append(f"**Mots** : {content['word_count']}")
    
    if meta:
        summary_parts.append(' | '.join(meta) + '\n')
    
    # Description
    if content.get('description'):
        summary_parts.append(f"_{content['description']}_\n")
    
    # Contenu
    if content.get('content'):
        summary_parts.append(f"\n{content['content']}")
    
    return '\n'.join(summary_parts)
