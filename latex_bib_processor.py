import re
import os
from pathlib import Path
from collections import OrderedDict

class LaTeXBibProcessor:
    """
    Professional LaTeX Bibliography Processor
    
    A comprehensive tool for processing LaTeX citations and reorganizing BibTeX files.
    Designed to clean, deduplicate, and reorder bibliography entries based on 
    citation appearance order in LaTeX documents.
    
    Key Features:
    - Extracts citations from LaTeX files supporting multiple citation commands
    - Parses BibTeX entries while preserving original formatting
    - Identifies missing and unused bibliography entries
    - Generates ordered BibTeX files based on citation sequence
    - Provides detailed analysis and reporting
    
    Usage:
        processor = LaTeXBibProcessor('document.tex', 'references.bib')
        processor.execute_full_process('ordered_refs.bib')
    """
    
    def __init__(self, tex_file, bib_file):
        """
        Initialize the processor with LaTeX and BibTeX file paths.
        
        Args:
            tex_file (str): Path to the LaTeX file
            bib_file (str): Path to the BibTeX file
        """
        self.tex_file = tex_file
        self.bib_file = bib_file
        self.tex_content = ""
        self.bib_content = ""
        
        # Citation tracking
        self.cited_keys = []  # All citations in order (with duplicates)
        self.unique_cited_keys = []  # Unique citations preserving order
        
        # BibTeX data
        self.bib_entries = {}  # key -> complete entry content
        self.bib_keys = set()  # All available keys in .bib
        
        # Analysis results
        self.missing_keys = []  # Cited but not in .bib
        self.unused_keys = []   # In .bib but not cited
        self.ordered_entries = OrderedDict()  # Final ordered entries
        
        # Comprehensive citation command patterns
        self.citation_patterns = [
            r'\\cite\{([^}]+)\}',           # \cite{key1,key2}
            r'\\citep\{([^}]+)\}',          # \citep{key1,key2}
            r'\\citet\{([^}]+)\}',          # \citet{key1,key2}
            r'\\citealp\{([^}]+)\}',        # \citealp{key1,key2}
            r'\\citealt\{([^}]+)\}',        # \citealt{key1,key2}
            r'\\citeauthor\{([^}]+)\}',     # \citeauthor{key1,key2}
            r'\\citeyear\{([^}]+)\}',       # \citeyear{key1,key2}
            r'\\nocite\{([^}]+)\}',         # \nocite{key1,key2}
            r'\\Cite\{([^}]+)\}',           # \Cite{key1,key2}
            r'\\Citep\{([^}]+)\}',          # \Citep{key1,key2}
            r'\\Citet\{([^}]+)\}',          # \Citet{key1,key2}
        ]
        
        # Enhanced BibTeX entry pattern - handles complex nested structures
        self.bib_entry_pattern = re.compile(
            r'(@\w+\s*\{\s*([^,\s}]+)\s*,.*?)(?=\n\s*@|\n\s*$|\Z)',
            re.DOTALL | re.MULTILINE
        )
    
    def load_files(self):
        """Load and validate both LaTeX and BibTeX files."""
        # Load LaTeX file
        try:
            with open(self.tex_file, 'r', encoding='utf-8') as f:
                self.tex_content = f.read()
            print(f"✓ Successfully loaded LaTeX file: {self.tex_file}")
            print(f"  File size: {len(self.tex_content):,} characters")
        except FileNotFoundError:
            raise FileNotFoundError(f"LaTeX file not found: {self.tex_file}")
        except UnicodeDecodeError:
            # Try alternative encodings
            try:
                with open(self.tex_file, 'r', encoding='latin-1') as f:
                    self.tex_content = f.read()
                print(f"✓ Loaded LaTeX file with latin-1 encoding: {self.tex_file}")
            except Exception as e:
                raise Exception(f"Error reading LaTeX file with multiple encodings: {e}")
        except Exception as e:
            raise Exception(f"Error reading LaTeX file: {e}")
        
        # Load BibTeX file
        try:
            with open(self.bib_file, 'r', encoding='utf-8') as f:
                self.bib_content = f.read()
            print(f"✓ Successfully loaded BibTeX file: {self.bib_file}")
            print(f"  File size: {len(self.bib_content):,} characters")
        except FileNotFoundError:
            raise FileNotFoundError(f"BibTeX file not found: {self.bib_file}")
        except UnicodeDecodeError:
            try:
                with open(self.bib_file, 'r', encoding='latin-1') as f:
                    self.bib_content = f.read()
                print(f"✓ Loaded BibTeX file with latin-1 encoding: {self.bib_file}")
            except Exception as e:
                raise Exception(f"Error reading BibTeX file with multiple encodings: {e}")
        except Exception as e:
            raise Exception(f"Error reading BibTeX file: {e}")
    
    def extract_citations_from_tex(self):
        """
        Extract all citation keys from LaTeX file in order of appearance.
        Supports multiple citation commands and handles comma-separated keys.
        """
        self.cited_keys = []
        citations_with_pos = []
        
        # Process each citation pattern
        for pattern in self.citation_patterns:
            matches = re.finditer(pattern, self.tex_content, re.IGNORECASE)
            for match in matches:
                pos = match.start()
                keys_str = match.group(1)
                
                # Handle comma-separated keys
                keys = [key.strip() for key in keys_str.split(',')]
                for key in keys:
                    if key and not key.isspace():  # Skip empty or whitespace-only keys
                        citations_with_pos.append((pos, key))
        
        # Sort by position to maintain document order
        citations_with_pos.sort(key=lambda x: x[0])
        
        # Extract ordered keys
        self.cited_keys = [key for pos, key in citations_with_pos]
        
        # Create unique list preserving first appearance order
        seen = set()
        self.unique_cited_keys = []
        for key in self.cited_keys:
            if key not in seen:
                self.unique_cited_keys.append(key)
                seen.add(key)
        
        print(f"✓ Citation extraction completed:")
        print(f"  Total citations found: {len(self.cited_keys)}")
        print(f"  Unique citation keys: {len(self.unique_cited_keys)}")
        
        return self.unique_cited_keys
    
    def parse_bib_entries(self):
        """
        Parse all BibTeX entries from .bib file.
        Preserves original formatting and handles complex entry structures.
        """
        self.bib_entries = {}
        self.bib_keys = set()
        
        # Find all BibTeX entries
        matches = self.bib_entry_pattern.findall(self.bib_content)
        
        for full_entry, key in matches:
            # Clean and validate key
            clean_key = key.strip()
            if clean_key:  # Skip empty keys
                self.bib_keys.add(clean_key)
                # Store complete entry preserving original formatting
                self.bib_entries[clean_key] = full_entry.strip()
        
        print(f"✓ BibTeX parsing completed:")
        print(f"  Total entries parsed: {len(self.bib_entries)}")
        print(f"  Valid entry keys: {len(self.bib_keys)}")
        
        return self.bib_entries
    
    def analyze_citations(self):
        """
        Perform comprehensive citation analysis.
        Identifies missing citations and unused bibliography entries.
        """
        cited_set = set(self.unique_cited_keys)
        
        # Identify missing entries (cited in .tex but not in .bib)
        self.missing_keys = [key for key in self.unique_cited_keys if key not in self.bib_keys]
        
        # Identify unused entries (in .bib but not cited in .tex)
        self.unused_keys = sorted(list(self.bib_keys - cited_set))
        
        # Calculate statistics
        total_cited = len(self.unique_cited_keys)
        total_in_bib = len(self.bib_keys)
        available = total_cited - len(self.missing_keys)
        
        print(f"\n📊 **Citation Analysis Summary**")
        print(f"   • Unique citations in LaTeX: {total_cited}")
        print(f"   • Total entries in BibTeX: {total_in_bib}")
        print(f"   • Available entries: {available}")
        print(f"   • Missing entries: {len(self.missing_keys)}")
        print(f"   • Unused entries: {len(self.unused_keys)}")
        
        return self.missing_keys, self.unused_keys
    
    def print_detailed_analysis(self):
        """Print comprehensive analysis results with actionable information."""
        
        if self.missing_keys:
            print(f"\n❌ **Missing Bibliography Entries** ({len(self.missing_keys)} items)")
            print("   The following citations appear in your LaTeX file but are missing from the BibTeX file:")
            print("   " + "-" * 70)
            for i, key in enumerate(self.missing_keys, 1):
                print(f"   {i:2d}. {key}")
            print("\n   ⚠️  Action Required: Add these entries to your .bib file or remove citations from .tex")
        
        if self.unused_keys:
            print(f"\n🗑️  **Unused Bibliography Entries** ({len(self.unused_keys)} items)")
            print("   The following entries exist in your BibTeX file but are not cited:")
            print("   " + "-" * 70)
            for i, key in enumerate(self.unused_keys, 1):
                print(f"   {i:2d}. {key}")
            print("\n   ℹ️  These entries will be excluded from the ordered output file")
        
        if not self.missing_keys and not self.unused_keys:
            print(f"\n✅ **Perfect Bibliography Match**")
            print("   All citations have corresponding entries, and no unused entries found!")
    
    def create_ordered_bib(self):
        """
        Create ordered BibTeX entries based on citation order in LaTeX file.
        Only includes entries that are both cited and available in the .bib file.
        """
        self.ordered_entries = OrderedDict()
        
        for key in self.unique_cited_keys:
            if key in self.bib_entries:
                self.ordered_entries[key] = self.bib_entries[key]
        
        print(f"\n✓ Created ordered bibliography:")
        print(f"  Entries included: {len(self.ordered_entries)}")
        print(f"  Ordering based on: Citation appearance in LaTeX file")
        
        return self.ordered_entries
    
    def save_ordered_bib(self, output_file="refs_ordered.bib"):
        """
        Save the ordered and cleaned BibTeX file.
        
        Args:
            output_file (str): Output filename for the ordered BibTeX file
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.ordered_entries:
            print("⚠️  No entries to save. Run create_ordered_bib() first.")
            return False
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                # Write header comment
                f.write(f"% Ordered Bibliography File\n")
                f.write(f"% Generated from: {self.tex_file} and {self.bib_file}\n")
                f.write(f"% Total entries: {len(self.ordered_entries)}\n")
                f.write(f"% Ordered by citation appearance in LaTeX document\n\n")
                
                # Write entries with proper spacing
                for i, (key, entry) in enumerate(self.ordered_entries.items()):
                    if i > 0:  # Add separation between entries
                        f.write('\n')
                    f.write(entry)
                    if not entry.endswith('\n'):
                        f.write('\n')
            
            print(f"✅ **Success**: Ordered BibTeX file saved as '{output_file}'")
            print(f"   📁 File location: {os.path.abspath(output_file)}")
            return True
            
        except Exception as e:
            print(f"❌ **Error**: Failed to save ordered BibTeX file: {e}")
            return False
    
    def print_citation_order(self, max_display=25):
        """
        Display the citation order for verification purposes.
        
        Args:
            max_display (int): Maximum number of entries to display
        """
        display_count = min(max_display, len(self.unique_cited_keys))
        
        print(f"\n📋 **Citation Order Preview** (showing first {display_count} of {len(self.unique_cited_keys)} entries)")
        print("=" * 80)
        print("Order | Status | Citation Key")
        print("-" * 80)
        
        for i, key in enumerate(self.unique_cited_keys[:display_count], 1):
            status = "✓ Available" if key in self.bib_entries else "❌ Missing"
            print(f"{i:5d} | {status:11s} | {key}")
        
        if len(self.unique_cited_keys) > max_display:
            remaining = len(self.unique_cited_keys) - max_display
            print(f"      | ...        | ... and {remaining} more entries")
        
        print("=" * 80)
    
    def generate_comprehensive_report(self):
        """Generate a detailed summary report of the entire process."""
        total_cited = len(self.unique_cited_keys)
        total_in_bib = len(self.bib_keys)
        available_entries = len(self.ordered_entries)
        missing_count = len(self.missing_keys)
        unused_count = len(self.unused_keys)
        
        # Calculate metrics
        coverage = (available_entries / total_cited * 100) if total_cited > 0 else 0
        efficiency = (available_entries / total_in_bib * 100) if total_in_bib > 0 else 0
        
        print(f"\n" + "=" * 90)
        print(f"📊 **COMPREHENSIVE PROCESSING REPORT**")
        print(f"=" * 90)
        
        print(f"📄 **Source Files:**")
        print(f"   • LaTeX document: {self.tex_file}")
        print(f"   • BibTeX database: {self.bib_file}")
        
        print(f"\n📈 **Processing Statistics:**")
        print(f"   • Total citations in LaTeX: {len(self.cited_keys):,} (including duplicates)")
        print(f"   • Unique citation keys: {total_cited:,}")
        print(f"   • Total BibTeX entries: {total_in_bib:,}")
        print(f"   • Successfully matched: {available_entries:,}")
        print(f"   • Missing from BibTeX: {missing_count:,}")
        print(f"   • Unused in BibTeX: {unused_count:,}")
        
        print(f"\n📊 **Quality Metrics:**")
        print(f"   • Citation Coverage: {coverage:.1f}% ({available_entries}/{total_cited})")
        print(f"   • BibTeX Efficiency: {efficiency:.1f}% ({available_entries}/{total_in_bib})")
        
        print(f"\n🎯 **Recommendations:**")
        if missing_count > 0:
            print(f"   • Add {missing_count} missing entries to improve coverage")
        if unused_count > 0:
            print(f"   • Consider removing {unused_count} unused entries to improve efficiency")
        if missing_count == 0 and unused_count == 0:
            print(f"   • Bibliography is perfectly optimized!")
        
        print(f"=" * 90)
    
    def execute_full_process(self, output_file="refs_ordered.bib"):
        """
        Execute the complete bibliography processing workflow.
        
        Args:
            output_file (str): Output filename for the ordered BibTeX file
            
        Returns:
            bool: True if process completed successfully, False otherwise
        """
        print("🚀 === LaTeX Bibliography Processing Started ===\n")
        
        try:
            # Step 1: Load and validate files
            print("📂 Step 1: Loading files...")
            self.load_files()
            
            # Step 2: Extract citations from LaTeX
            print("\n🔍 Step 2: Extracting citations from LaTeX...")
            self.extract_citations_from_tex()
            
            # Step 3: Parse BibTeX entries
            print("\n📚 Step 3: Parsing BibTeX entries...")
            self.parse_bib_entries()
            
            # Step 4: Analyze citations and entries
            print("\n🔬 Step 4: Analyzing citations...")
            self.analyze_citations()
            
            # Step 5: Display detailed analysis
            print("\n📋 Step 5: Detailed analysis results...")
            self.print_detailed_analysis()
            
            # Step 6: Show citation order preview
            print("\n👀 Step 6: Citation order preview...")
            self.print_citation_order()
            
            # Step 7: Create ordered bibliography
            print("\n⚡ Step 7: Creating ordered bibliography...")
            self.create_ordered_bib()
            
            # Step 8: Save ordered file
            print("\n💾 Step 8: Saving ordered BibTeX file...")
            success = self.save_ordered_bib(output_file)
            
            # Step 9: Generate comprehensive report
            print("\n📊 Step 9: Generating final report...")
            self.generate_comprehensive_report()
            
            # Final status
            if success:
                print(f"\n🎉 **PROCESS COMPLETED SUCCESSFULLY**")
                print(f"📁 **Output file**: {output_file}")
                print(f"✨ **Ready to use**: Your ordered bibliography is ready!")
            else:
                print(f"\n⚠️  **PROCESS COMPLETED WITH ISSUES**")
                print(f"❌ **File save failed**: Check permissions and try again")
            
            return success
            
        except Exception as e:
            print(f"\n💥 **CRITICAL ERROR**: {e}")
            print(f"❌ **Process terminated**: Please check your input files and try again")
            return False

# Usage example for your specific files
if __name__ == "__main__":
    # Initialize processor with your files
    processor = LaTeXBibProcessor('KPNs-Mining.tex', 'refs.bib')
    
    # Execute complete processing workflow
    success = processor.execute_full_process('refs_ordered.bib')
    
    if success:
        print("\n✅ Bibliography processing completed successfully!")
        print("🔄 You can now replace your original refs.bib with refs_ordered.bib")
    else:
        print("\n❌ Processing failed. Please check the error messages above.")