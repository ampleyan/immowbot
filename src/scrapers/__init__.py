"""
Scrapers package for different Belgian real estate websites.
"""
from .immoweb_scraper import ImmowebScraper
from .immoscoop_scraper import ImmoscoopScraper
from .zimmo_scraper import ZimmoScraper
from .realo_scraper import RealoScraper
from .immovlan_scraper import ImmovlanScraper

__all__ = ['ImmowebScraper', 'ImmoscoopScraper', 'ZimmoScraper', 'RealoScraper', 'ImmovlanScraper']
