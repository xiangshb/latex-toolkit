import re
import os
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ImageInfo:
    """Data class to store image information"""
    full_command: str
    path: str
    prefix: str
    suffix: str
    position_in_doc: int

@dataclass
class FigureEnvironment:
    """Data class to store figure environment information"""
    position: int
    content: str
    images: List[ImageInfo]

@dataclass
class ProcessingResult:
    """Data class to store processing results"""
    figure_label: str
    original_path: str
    new_path: str
    needs_rename: bool

class TeXFigureProcessor:
    """
    A comprehensive LaTeX figure processor that analyzes, reorganizes, and renames
    figures based on their order in the document.
    """
    
    # Class constants
    IMAGE_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.eps', '.svg'}
    FIGURE_KEYWORDS = {'figure', 'fig', 'image'}
    
    def __init__(self, tex_file: str):
        """
        Initialize the processor with a LaTeX file.
        
        Args:
            tex_file: Path to the LaTeX file to process
        """
        self.tex_file = Path(tex_file)
        if not self.tex_file.exists():
            raise FileNotFoundError(f"LaTeX file not found: {tex_file}")
            
        self.tex_content = ""
        self.modifications: Dict[str, str] = {}
        self.results: List[ProcessingResult] = []
        self.figure_environments: List[FigureEnvironment] = []
        
        # Compile regex patterns
        self._compile_patterns()
        
        logger.info(f"Initialized processor for: {self.tex_file}")
    
    def _compile_patterns(self):
        """Compile all regex patterns used in processing"""
        # Pattern for includegraphics commands
        self.img_pattern = re.compile(
            r'(\\includegraphics(?:\s*\[[^\]]*\])*\s*\{)([^}]+)(\})',
            re.MULTILINE
        )
        
        # Pattern for figure environments (including figure*)
        self.figure_pattern = re.compile(
            r'\\begin\{figure\*?\}.*?\\end\{figure\*?\}',
            re.DOTALL | re.MULTILINE
        )
        
        # Pattern for existing figure prefixes
        self.prefix_pattern = re.compile(r'^fig_s?(\d+)_(.+)$')
        
        # Pattern for appendix
        self.appendix_pattern = re.compile(r'\\appendix\b')
    
    def load_tex_file(self) -> None:
        """Load the LaTeX file content"""
        try:
            with open(self.tex_file, 'r', encoding='utf-8') as f:
                self.tex_content = f.read()
            logger.info(f"Loaded LaTeX file: {self.tex_file}")
        except Exception as e:
            logger.error(f"Failed to load LaTeX file: {e}")
            raise
    
    def is_image_file(self, path: str) -> bool:
        """
        Determine if a path refers to an image file.
        
        Args:
            path: File path to check
            
        Returns:
            True if the path appears to be an image file
        """
        path_lower = path.lower()
        
        # Check file extension
        if any(path_lower.endswith(ext) for ext in self.IMAGE_EXTENSIONS):
            return True
        
        # Check if path contains image-related keywords
        if any(keyword in path_lower for keyword in self.FIGURE_KEYWORDS):
            return True
            
        # Check if it's a file without extension in a figures directory
        path_obj = Path(path)
        if not path_obj.suffix and any(keyword in path_lower for keyword in self.FIGURE_KEYWORDS):
            return True
            
        return False
    
    def extract_figure_environments(self) -> List[FigureEnvironment]:
        """
        Extract all figure environments and their contained images.
        
        Returns:
            List of FigureEnvironment objects
        """
        if not self.tex_content:
            self.load_tex_file()
        
        figure_matches = list(self.figure_pattern.finditer(self.tex_content))
        
        for match in figure_matches:
            figure_content = match.group(0)
            figure_start = match.start()
            
            # Find all images in this figure environment
            images_in_figure = []
            img_matches = self.img_pattern.findall(figure_content)
            
            for img_match in img_matches:
                image_path = img_match[1].strip()
                if self.is_image_file(image_path):
                    full_command = img_match[0] + img_match[1] + img_match[2]
                    # Find exact position in document
                    cmd_start = self.tex_content.find(full_command, figure_start)
                    
                    if cmd_start != -1:  # Only add if found
                        images_in_figure.append(ImageInfo(
                            full_command=full_command,
                            path=image_path,
                            prefix=img_match[0],
                            suffix=img_match[2],
                            position_in_doc=cmd_start
                        ))
            
            if images_in_figure:  # Only keep figure environments with images
                # Sort images by position within figure
                images_in_figure.sort(key=lambda x: x.position_in_doc)
                
                self.figure_environments.append(FigureEnvironment(
                    position=figure_start,
                    content=figure_content,
                    images=images_in_figure
                ))
        
        # Sort figure environments by document position
        self.figure_environments.sort(key=lambda x: x.position)
        
        total_images = sum(len(fig.images) for fig in self.figure_environments)
        logger.info(f"Found {len(self.figure_environments)} figure environments with {total_images} images")
        
        return self.figure_environments
    
    def find_appendix_position(self) -> int:
        """
        Find the position of the appendix in the document.
        
        Returns:
            Position of appendix, or end of document if not found
        """
        appendix_match = self.appendix_pattern.search(self.tex_content)
        return appendix_match.start() if appendix_match else len(self.tex_content)
    
    def categorize_figures_by_position(self) -> Tuple[List[FigureEnvironment], List[FigureEnvironment]]:
        """
        Categorize figures as main text or appendix based on position.
        
        Returns:
            Tuple of (main_figures, appendix_figures)
        """
        appendix_pos = self.find_appendix_position()
        
        main_figures = []
        appendix_figures = []
        
        for fig_env in self.figure_environments:
            if fig_env.position < appendix_pos:
                main_figures.append(fig_env)
            else:
                appendix_figures.append(fig_env)
        
        return main_figures, appendix_figures
    
    def extract_directory_and_filename(self, path: str) -> Tuple[str, str]:
        """
        Extract directory and filename from a path.
        
        Args:
            path: File path to split
            
        Returns:
            Tuple of (directory, filename)
        """
        if '/' in path:
            parts = path.rsplit('/', 1)
            if len(parts) == 2:
                return parts[0] + '/', parts[1]
        return '', path
    
    def generate_new_filename(self, filename: str, expected_prefix: str) -> str:
        """
        Generate new filename with the expected prefix.
        
        Args:
            filename: Original filename
            expected_prefix: Desired prefix (e.g., "fig_1_")
            
        Returns:
            New filename with correct prefix
        """
        existing_match = self.prefix_pattern.match(filename)
        
        if existing_match:
            base_name = existing_match.group(2)
            return expected_prefix + base_name
        else:
            return expected_prefix + filename
    
    def process_single_image(self, img_info: ImageInfo, prefix: str, fig_label: str) -> None:
        """
        Process a single image and add to results.
        
        Args:
            img_info: Image information
            prefix: Expected filename prefix
            fig_label: Figure label for display
        """
        orig_path = img_info.path
        dir_part, filename = self.extract_directory_and_filename(orig_path)
        new_filename = self.generate_new_filename(filename, prefix)
        new_path = dir_part + new_filename
        
        needs_rename = orig_path != new_path
        
        self.results.append(ProcessingResult(
            figure_label=fig_label,
            original_path=orig_path,
            new_path=new_path,
            needs_rename=needs_rename
        ))
        
        if needs_rename:
            old_full = img_info.full_command
            new_full = img_info.prefix + new_path + img_info.suffix
            self.modifications[old_full] = new_full
    
    def analyze_all_figures(self) -> List[ProcessingResult]:
        """
        Analyze all figure environments and generate renaming scheme.
        
        Returns:
            List of ProcessingResult objects
        """
        self.extract_figure_environments()
        main_figures, appendix_figures = self.categorize_figures_by_position()
        
        # Process main text figures
        for fig_idx, fig_env in enumerate(main_figures, 1):
            fig_label = f"Fig {fig_idx}"
            prefix = f"fig_{fig_idx}_"
            
            for img_info in fig_env.images:
                self.process_single_image(img_info, prefix, fig_label)
        
        # Process appendix figures
        for fig_idx, fig_env in enumerate(appendix_figures, 1):
            fig_label = f"Fig S{fig_idx}"
            prefix = f"fig_s{fig_idx}_"
            
            for img_info in fig_env.images:
                self.process_single_image(img_info, prefix, fig_label)
        
        return self.results
    
    def print_results(self) -> None:
        """Print analysis results in a formatted table"""
        if not self.results:
            logger.warning("No results to display")
            return
            
        print("\n" + "="*100)
        print("Figure Order | Original Image Name                     | Modified Image Name")
        print("-" * 100)
        
        for result in self.results:
            print(f"{result.figure_label:12} | {result.original_path:45} | {result.new_path}")
        
        print("="*100)
    
    def print_summary(self) -> None:
        """Print processing summary statistics"""
        if not self.results:
            logger.warning("No results to summarize")
            return
            
        main_count = len([r for r in self.results if not r.figure_label.startswith('Fig S')])
        appendix_count = len([r for r in self.results if r.figure_label.startswith('Fig S')])
        modified_count = len([r for r in self.results if r.needs_rename])
        
        main_figures, appendix_figures = self.categorize_figures_by_position()
        
        print(f"\n📊 **Processing Summary**")
        print(f"   • Total figure environments: {len(self.figure_environments)}")
        print(f"   • Main text figures: {len(main_figures)}")
        print(f"   • Appendix figures: {len(appendix_figures)}")
        print(f"   • Total images found: {len(self.results)}")
        print(f"   • Main text images: {main_count}")
        print(f"   • Appendix images: {appendix_count}")
        print(f"   • Images to be renamed: {modified_count}")
        print(f"   • Images already correct: {len(self.results) - modified_count}")
    
    def save_modified_tex(self, output_filename: Optional[str] = None) -> bool:
        """
        Save the modified LaTeX file with updated image paths.
        
        Args:
            output_filename: Output filename (defaults to original_name_reset.tex)
            
        Returns:
            True if modifications were made and saved, False otherwise
        """
        if not self.modifications:
            logger.info("No modifications needed - all prefixes are correct!")
            return False
        
        if output_filename is None:
            output_filename = self.tex_file.stem + "_reset.tex"
        
        new_content = self.tex_content
        
        # Sort modifications by position (reverse order to avoid position shifts)
        sorted_modifications = sorted(
            self.modifications.items(),
            key=lambda x: self.tex_content.find(x[0]),
            reverse=True
        )
        
        for old, new in sorted_modifications:
            if old in new_content:
                new_content = new_content.replace(old, new, 1)
            else:
                logger.warning(f"Could not find command to replace: {old}")
        
        try:
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(new_content)
            logger.info(f"Modified LaTeX file saved as: {output_filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to save modified LaTeX file: {e}")
            raise
    
    def create_output_directory(self, dir_name: str = "figures-reset") -> Path:
        """
        Create output directory for renamed figures.
        
        Args:
            dir_name: Directory name to create
            
        Returns:
            Path object for the created directory
        """
        output_dir = Path(dir_name)
        
        if output_dir.exists():
            logger.info(f"Directory {output_dir} already exists")
        else:
            output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {output_dir}")
        
        return output_dir
    
    def copy_and_rename_figures(self, output_dir: str = "figures-reset") -> Dict[str, int]:
        """
        Copy and rename figure files to the output directory.
        
        Args:
            output_dir: Output directory name
            
        Returns:
            Dictionary with copy statistics
        """
        reset_folder = self.create_output_directory(output_dir)
        
        stats = {
            'copied': 0,
            'skipped': 0,
            'failed': 0
        }
        
        failed_copies = []
        
        for result in self.results:
            source_file = Path(result.original_path)
            
            if result.needs_rename:
                # File needs renaming
                _, new_filename = self.extract_directory_and_filename(result.new_path)
                target_file = reset_folder / new_filename
            else:
                # File doesn't need renaming
                _, filename = self.extract_directory_and_filename(result.original_path)
                target_file = reset_folder / filename
            
            try:
                if not source_file.exists():
                    failed_copies.append(f"Source not found: {source_file}")
                    stats['failed'] += 1
                    continue
                
                if target_file.exists():
                    logger.info(f"Skipped (already exists): {target_file.name}")
                    stats['skipped'] += 1
                    continue
                
                shutil.copy2(source_file, target_file)
                action = "Renamed and copied" if result.needs_rename else "Copied"
                logger.info(f"{action}: {source_file.name} → {target_file.name}")
                stats['copied'] += 1
                
            except Exception as e:
                failed_copies.append(f"Failed to copy {source_file}: {str(e)}")
                stats['failed'] += 1
        
        logger.info(f"Copy operation completed: {stats['copied']} copied, {stats['skipped']} skipped, {stats['failed']} failed")
        
        if failed_copies:
            logger.warning(f"Failed operations ({len(failed_copies)}):")
            for failure in failed_copies:
                logger.warning(f"   {failure}")
        
        return stats
    
    def execute_full_processing(self, output_dir: str = "figures-reset", 
                              tex_output: Optional[str] = None) -> List[ProcessingResult]:
        """
        Execute the complete figure processing workflow.
        
        Args:
            output_dir: Directory for output figures
            tex_output: Output LaTeX filename
            
        Returns:
            List of processing results
        """
        logger.info("=== Starting LaTeX Figure Processing ===")
        
        try:
            # Step 1: Analyze all figures
            self.analyze_all_figures()
            self.print_summary()
            self.print_results()
            
            # Step 2: Save modified LaTeX file
            tex_saved = self.save_modified_tex(tex_output)
            
            # Step 3: Copy and rename figure files
            copy_stats = self.copy_and_rename_figures(output_dir)
            
            logger.info("=== Processing Complete ===")
            logger.info(f"Total modifications made: {len(self.modifications)}")
            logger.info(f"Files processed: {copy_stats}")
            
            return self.results
            
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            raise

# Example usage and testing
if __name__ == "__main__":
    # This would be used with an actual LaTeX file
    processor = TeXFigureProcessor('your_paper.tex')
    # Execute full processing workflow
    results = processor.execute_full_processing(
        output_dir="figures-renamed",
        tex_output="paper_with_renamed_figures.tex"
    )

    # Or run individual steps
    processor.analyze_all_figures()
    processor.print_summary()
    processor.save_modified_tex()
    processor.copy_and_rename_figures()