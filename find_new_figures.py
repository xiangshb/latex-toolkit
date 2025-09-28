import re
import os
import shutil
from pathlib import Path
from typing import Set, List, Tuple, Optional
import logging
from dataclasses import dataclass

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ComparisonResult:
    """Data class to store comparison results"""
    old_images: Set[str]
    new_images: Set[str]
    added_images: Set[str]
    removed_images: Set[str]
    common_images: Set[str]

@dataclass
class CopyResult:
    """Data class to store copy operation results"""
    copied: List[str]
    missing: List[str]
    failed: List[str]
    total_attempted: int

class LaTeXImageExtractor:
    """
    A utility class for extracting and comparing images referenced in LaTeX documents.
    """
    
    # Default image extensions to consider
    DEFAULT_IMAGE_EXTENSIONS = ['.pdf', '.png', '.jpg', '.jpeg', '.eps', '.svg']
    
    def __init__(self, image_extensions: Optional[List[str]] = None):
        """
        Initialize the extractor with specified image extensions.
        
        Args:
            image_extensions: List of image file extensions to consider
        """
        self.image_extensions = image_extensions or self.DEFAULT_IMAGE_EXTENSIONS
        self.includegraphics_pattern = re.compile(
            r'\\includegraphics(?:\s*\[[^\]]*\])?\s*\{([^}]+)\}',
            re.MULTILINE
        )
        
        logger.info(f"Initialized extractor with extensions: {self.image_extensions}")
    
    def extract_images_from_tex(self, tex_file: str) -> Set[str]:
        """
        Extract all image files referenced in a LaTeX document.
        
        Args:
            tex_file: Path to the LaTeX file
            
        Returns:
            Set of image filenames found in the document
            
        Raises:
            FileNotFoundError: If the LaTeX file doesn't exist
            IOError: If there's an error reading the file
        """
        tex_path = Path(tex_file)
        
        if not tex_path.exists():
            raise FileNotFoundError(f"LaTeX file not found: {tex_file}")
        
        try:
            with open(tex_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            raise IOError(f"Error reading LaTeX file {tex_file}: {e}")
        
        # Find all includegraphics commands
        matches = self.includegraphics_pattern.findall(content)
        
        image_files = set()
        
        for match in matches:
            # Clean the path (remove leading/trailing whitespace)
            image_path = match.strip()
            
            # Extract just the filename
            filename = os.path.basename(image_path)
            
            # Split filename and extension
            name, ext = os.path.splitext(filename)
            
            if ext:
                # File has extension, add it directly
                image_files.add(filename)
            else:
                # File has no extension, try all possible extensions
                for extension in self.image_extensions:
                    image_files.add(name + extension)
        
        logger.info(f"Extracted {len(image_files)} image references from {tex_file}")
        return image_files
    
    def compare_tex_files(self, old_tex: str, new_tex: str) -> ComparisonResult:
        """
        Compare image references between two LaTeX files.
        
        Args:
            old_tex: Path to the old LaTeX file
            new_tex: Path to the new LaTeX file
            
        Returns:
            ComparisonResult object with comparison details
        """
        logger.info(f"Comparing images between {old_tex} and {new_tex}")
        
        old_images = self.extract_images_from_tex(old_tex)
        new_images = self.extract_images_from_tex(new_tex)
        
        added_images = new_images - old_images
        removed_images = old_images - new_images
        common_images = old_images & new_images
        
        result = ComparisonResult(
            old_images=old_images,
            new_images=new_images,
            added_images=added_images,
            removed_images=removed_images,
            common_images=common_images
        )
        
        logger.info(f"Comparison complete: {len(added_images)} added, "
                   f"{len(removed_images)} removed, {len(common_images)} common")
        
        return result
    
    def print_comparison_summary(self, result: ComparisonResult, 
                               old_file: str, new_file: str) -> None:
        """
        Print a detailed comparison summary.
        
        Args:
            result: ComparisonResult object
            old_file: Name of the old file for display
            new_file: Name of the new file for display
        """
        print(f"\n📊 **Image Comparison Summary**")
        print(f"   Old file ({old_file}): {len(result.old_images)} images")
        print(f"   New file ({new_file}): {len(result.new_images)} images")
        print(f"   Common images: {len(result.common_images)}")
        print(f"   Added images: {len(result.added_images)}")
        print(f"   Removed images: {len(result.removed_images)}")
        
        if result.added_images:
            print(f"\n✅ **Images added in {new_file}:**")
            for img in sorted(result.added_images):
                print(f"   + {img}")
        else:
            print(f"\n✅ No new images were added in {new_file}")
        
        if result.removed_images:
            print(f"\n❌ **Images removed from {new_file}:**")
            for img in sorted(result.removed_images):
                print(f"   - {img}")
    
    def copy_images(self, image_list: Set[str], source_dir: str, 
                   destination_dir: str, create_dest: bool = True) -> CopyResult:
        """
        Copy a list of images from source to destination directory.
        
        Args:
            image_list: Set of image filenames to copy
            source_dir: Source directory path
            destination_dir: Destination directory path
            create_dest: Whether to create destination directory if it doesn't exist
            
        Returns:
            CopyResult object with operation details
        """
        source_path = Path(source_dir)
        dest_path = Path(destination_dir)
        
        if not source_path.exists():
            raise FileNotFoundError(f"Source directory not found: {source_dir}")
        
        if create_dest:
            dest_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured destination directory exists: {destination_dir}")
        
        copied = []
        missing = []
        failed = []
        
        for image in image_list:
            src_file = source_path / image
            dst_file = dest_path / image
            
            try:
                if src_file.exists():
                    # Check if destination already exists
                    if dst_file.exists():
                        logger.info(f"Skipped (already exists): {image}")
                        continue
                    
                    shutil.copy2(src_file, dst_file)
                    copied.append(image)
                    logger.info(f"Copied: {image}")
                else:
                    missing.append(image)
                    logger.warning(f"Source file not found: {src_file}")
            
            except Exception as e:
                failed.append(image)
                logger.error(f"Failed to copy {image}: {e}")
        
        result = CopyResult(
            copied=copied,
            missing=missing,
            failed=failed,
            total_attempted=len(image_list)
        )
        
        logger.info(f"Copy operation completed: {len(copied)} copied, "
                   f"{len(missing)} missing, {len(failed)} failed")
        
        return result
    
    def print_copy_summary(self, result: CopyResult, destination_dir: str) -> None:
        """
        Print a summary of the copy operation.
        
        Args:
            result: CopyResult object
            destination_dir: Destination directory for display
        """
        print(f"\n📁 **Copy Operation Summary**")
        print(f"   Total files attempted: {result.total_attempted}")
        print(f"   Successfully copied: {len(result.copied)}")
        print(f"   Missing from source: {len(result.missing)}")
        print(f"   Failed to copy: {len(result.failed)}")
        print(f"   Destination: {destination_dir}")
        
        if result.copied:
            print(f"\n✅ **Successfully copied files:**")
            for img in sorted(result.copied):
                print(f"   ✓ {img}")
        
        if result.missing:
            print(f"\n⚠️  **Files not found in source directory:**")
            for img in sorted(result.missing):
                print(f"   ? {img}")
        
        if result.failed:
            print(f"\n❌ **Failed to copy:**")
            for img in sorted(result.failed):
                print(f"   ✗ {img}")

class LaTeXImageManager:
    """
    High-level manager for LaTeX image operations.
    """
    
    def __init__(self, image_extensions: Optional[List[str]] = None):
        """Initialize the manager with an extractor."""
        self.extractor = LaTeXImageExtractor(image_extensions)
    
    def extract_and_copy_new_images(self, old_tex: str, new_tex: str, 
                                  source_dir: str, dest_dir: str) -> Tuple[ComparisonResult, CopyResult]:
        """
        Complete workflow: compare LaTeX files and copy new images.
        
        Args:
            old_tex: Path to old LaTeX file
            new_tex: Path to new LaTeX file
            source_dir: Source directory for images
            dest_dir: Destination directory for new images
            
        Returns:
            Tuple of (ComparisonResult, CopyResult)
        """
        logger.info("=== Starting LaTeX Image Management Workflow ===")
        
        # Step 1: Compare files
        comparison = self.extractor.compare_tex_files(old_tex, new_tex)
        self.extractor.print_comparison_summary(comparison, old_tex, new_tex)
        
        # Step 2: Copy new images if any
        if comparison.added_images:
            copy_result = self.extractor.copy_images(
                comparison.added_images, source_dir, dest_dir
            )
            self.extractor.print_copy_summary(copy_result, dest_dir)
        else:
            copy_result = CopyResult([], [], [], 0)
            print(f"\n📁 No images to copy.")
        
        logger.info("=== Workflow Complete ===")
        return comparison, copy_result

# Example usage and demonstration
def main():
    """Example usage of the LaTeX image management system."""
    
    # Configuration
    config = {
        'old_tex': 'KPNs-Mining-R0.tex',
        'new_tex': 'KPNs-Mining.tex',
        'source_dir': 'figures-all',
        'dest_dir': 'figures-new',
        'image_extensions': ['.pdf', '.png', '.jpg', '.jpeg']
    }
    
    try:
        # Initialize manager
        manager = LaTeXImageManager(config['image_extensions'])
        
        # Execute workflow
        comparison, copy_result = manager.extract_and_copy_new_images(
            config['old_tex'],
            config['new_tex'],
            config['source_dir'],
            config['dest_dir']
        )
        
        # Additional analysis if needed
        if comparison.removed_images:
            print(f"\n🔍 **Additional Analysis:**")
            print(f"   Consider reviewing removed images: {len(comparison.removed_images)} files")
        
        return comparison, copy_result
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return None, None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None, None

if __name__ == "__main__":
    # Initialize and run complete workflow
    manager = LaTeXImageManager(['.pdf', '.png', '.jpg', '.jpeg'])
    comparison, copy_result = manager.extract_and_copy_new_images(
        'old_paper.tex', 'new_paper.tex', 
        'figures-all', 'figures-new'
    )
    # Advanced Usage:
    # Use extractor directly for more control
    extractor = LaTeXImageExtractor(['.pdf', '.png', '.eps'])

    # Extract images from single file
    images = extractor.extract_images_from_tex('paper.tex')

    # Compare two files
    comparison = extractor.compare_tex_files('v1.tex', 'v2.tex')

    # Copy specific images
    copy_result = extractor.copy_images(
        comparison.added_images, 'source/', 'dest/'
    )
