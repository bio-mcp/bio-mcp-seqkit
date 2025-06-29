import asyncio
import json
import logging
import tempfile
from pathlib import Path
from typing import Any, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ErrorContent
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class ServerSettings(BaseSettings):
    max_file_size: int = 10_000_000_000  # 10GB for large sequence files
    temp_dir: Optional[str] = None
    timeout: int = 600  # 10 minutes
    seqkit_path: str = "seqkit"
    
    class Config:
        env_prefix = "BIO_MCP_"


class SeqKitServer:
    def __init__(self, settings: Optional[ServerSettings] = None):
        self.settings = settings or ServerSettings()
        self.server = Server("bio-mcp-seqkit")
        self._setup_handlers()
        
    def _setup_handlers(self):
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="seqkit_stats",
                    description="Get basic statistics of FASTA/FASTQ files",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "input_file": {
                                "type": "string",
                                "description": "Path to FASTA/FASTQ file"
                            },
                            "all_stats": {
                                "type": "boolean",
                                "default": False,
                                "description": "Show all statistics including N50"
                            }
                        },
                        "required": ["input_file"]
                    }
                ),
                Tool(
                    name="seqkit_subseq",
                    description="Extract subsequences by region",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "input_file": {
                                "type": "string",
                                "description": "Path to FASTA/FASTQ file"
                            },
                            "region": {
                                "type": "string",
                                "description": "Region (e.g., '1:100-200' or 'chr1:1000-2000')"
                            },
                            "bed_file": {
                                "type": "string",
                                "description": "BED file with regions to extract"
                            }
                        },
                        "required": ["input_file"]
                    }
                ),
                Tool(
                    name="seqkit_grep",
                    description="Search sequences by pattern or ID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "input_file": {
                                "type": "string",
                                "description": "Path to FASTA/FASTQ file"
                            },
                            "pattern": {
                                "type": "string",
                                "description": "Search pattern (regex supported)"
                            },
                            "pattern_file": {
                                "type": "string",
                                "description": "File with list of patterns/IDs"
                            },
                            "search_sequence": {
                                "type": "boolean",
                                "default": False,
                                "description": "Search in sequence instead of header"
                            },
                            "invert_match": {
                                "type": "boolean",
                                "default": False,
                                "description": "Invert match (exclude matching sequences)"
                            },
                            "ignore_case": {
                                "type": "boolean",
                                "default": False,
                                "description": "Ignore case"
                            }
                        },
                        "required": ["input_file"]
                    }
                ),
                Tool(
                    name="seqkit_seq",
                    description="Transform sequences (reverse, complement, etc.)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "input_file": {
                                "type": "string",
                                "description": "Path to FASTA/FASTQ file"
                            },
                            "reverse": {
                                "type": "boolean",
                                "default": False,
                                "description": "Reverse sequence"
                            },
                            "complement": {
                                "type": "boolean",
                                "default": False,
                                "description": "Complement sequence"
                            },
                            "reverse_complement": {
                                "type": "boolean",
                                "default": False,
                                "description": "Reverse complement sequence"
                            },
                            "rna2dna": {
                                "type": "boolean",
                                "default": False,
                                "description": "Convert RNA to DNA"
                            },
                            "dna2rna": {
                                "type": "boolean",
                                "default": False,
                                "description": "Convert DNA to RNA"
                            },
                            "translate": {
                                "type": "boolean",
                                "default": False,
                                "description": "Translate to protein"
                            },
                            "min_length": {
                                "type": "integer",
                                "description": "Minimum sequence length filter"
                            },
                            "max_length": {
                                "type": "integer",
                                "description": "Maximum sequence length filter"
                            }
                        },
                        "required": ["input_file"]
                    }
                ),
                Tool(
                    name="seqkit_sort",
                    description="Sort sequences by different criteria",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "input_file": {
                                "type": "string",
                                "description": "Path to FASTA/FASTQ file"
                            },
                            "sort_by": {
                                "type": "string",
                                "enum": ["id", "name", "seq", "length"],
                                "default": "id",
                                "description": "Sort criterion"
                            },
                            "reverse": {
                                "type": "boolean",
                                "default": False,
                                "description": "Reverse sort order"
                            },
                            "by_length": {
                                "type": "boolean",
                                "default": False,
                                "description": "Sort by sequence length"
                            }
                        },
                        "required": ["input_file"]
                    }
                ),
                Tool(
                    name="seqkit_rmdup",
                    description="Remove duplicate sequences",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "input_file": {
                                "type": "string",
                                "description": "Path to FASTA/FASTQ file"
                            },
                            "by_name": {
                                "type": "boolean",
                                "default": False,
                                "description": "Remove duplicates by sequence name"
                            },
                            "by_seq": {
                                "type": "boolean",
                                "default": True,
                                "description": "Remove duplicates by sequence"
                            },
                            "ignore_case": {
                                "type": "boolean",
                                "default": False,
                                "description": "Ignore case when comparing"
                            }
                        },
                        "required": ["input_file"]
                    }
                ),
                Tool(
                    name="seqkit_sample",
                    description="Sample sequences randomly",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "input_file": {
                                "type": "string",
                                "description": "Path to FASTA/FASTQ file"
                            },
                            "number": {
                                "type": "integer",
                                "description": "Number of sequences to sample"
                            },
                            "proportion": {
                                "type": "number",
                                "description": "Proportion of sequences to sample (0-1)"
                            },
                            "seed": {
                                "type": "integer",
                                "description": "Random seed for reproducible sampling"
                            }
                        },
                        "required": ["input_file"]
                    }
                ),
                Tool(
                    name="seqkit_convert",
                    description="Convert between FASTA and FASTQ formats",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "input_file": {
                                "type": "string",
                                "description": "Path to input file"
                            },
                            "output_format": {
                                "type": "string",
                                "enum": ["fasta", "fastq"],
                                "description": "Output format"
                            },
                            "line_width": {
                                "type": "integer",
                                "default": 0,
                                "description": "Line width for FASTA output (0 for no wrapping)"
                            }
                        },
                        "required": ["input_file", "output_format"]
                    }
                ),
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent | ErrorContent]:
            handlers = {
                "seqkit_stats": self._run_stats,
                "seqkit_subseq": self._run_subseq,
                "seqkit_grep": self._run_grep,
                "seqkit_seq": self._run_seq,
                "seqkit_sort": self._run_sort,
                "seqkit_rmdup": self._run_rmdup,
                "seqkit_sample": self._run_sample,
                "seqkit_convert": self._run_convert,
            }
            
            handler = handlers.get(name)
            if handler:
                return await handler(arguments)
            else:
                return [ErrorContent(text=f"Unknown tool: {name}")]
    
    async def _run_stats(self, arguments: dict) -> list[TextContent | ErrorContent]:
        try:
            input_file = Path(arguments["input_file"])
            if not input_file.exists():
                return [ErrorContent(text=f"Input file not found: {input_file}")]
            
            cmd = [self.settings.seqkit_path, "stats"]
            
            if arguments.get("all_stats"):
                cmd.append("-a")
            
            cmd.extend(["-T", str(input_file)])  # -T for tabular output
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                return [ErrorContent(text=f"seqkit stats failed: {stderr.decode()}")]
            
            return [TextContent(text=f"Sequence Statistics:\n\n{stdout.decode()}")]
            
        except Exception as e:
            logger.error(f"Error in seqkit stats: {e}", exc_info=True)
            return [ErrorContent(text=f"Error: {str(e)}")]
    
    async def _run_subseq(self, arguments: dict) -> list[TextContent | ErrorContent]:
        try:
            input_file = Path(arguments["input_file"])
            if not input_file.exists():
                return [ErrorContent(text=f"Input file not found: {input_file}")]
            
            with tempfile.TemporaryDirectory(dir=self.settings.temp_dir) as tmpdir:
                output_file = Path(tmpdir) / f"subseq.{input_file.suffix}"
                
                cmd = [self.settings.seqkit_path, "subseq"]
                
                if arguments.get("region"):
                    cmd.extend(["-r", arguments["region"]])
                elif arguments.get("bed_file"):
                    bed_file = Path(arguments["bed_file"])
                    if bed_file.exists():
                        cmd.extend(["--bed", str(bed_file)])
                    else:
                        return [ErrorContent(text=f"BED file not found: {bed_file}")]
                else:
                    return [ErrorContent(text="Either 'region' or 'bed_file' must be specified")]
                
                cmd.extend(["-o", str(output_file), str(input_file)])
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    return [ErrorContent(text=f"seqkit subseq failed: {stderr.decode()}")]
                
                # Count sequences in output
                stats_cmd = [self.settings.seqkit_path, "stats", "-T", str(output_file)]
                stats_process = await asyncio.create_subprocess_exec(
                    *stats_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stats_out, _ = await stats_process.communicate()
                
                return [TextContent(
                    text=f"Subsequence extraction completed!\n\n"
                         f"Output file: {output_file}\n"
                         f"Region: {arguments.get('region', 'BED file regions')}\n\n"
                         f"Output statistics:\n{stats_out.decode()}"
                )]
                
        except Exception as e:
            logger.error(f"Error in seqkit subseq: {e}", exc_info=True)
            return [ErrorContent(text=f"Error: {str(e)}")]
    
    async def _run_grep(self, arguments: dict) -> list[TextContent | ErrorContent]:
        try:
            input_file = Path(arguments["input_file"])
            if not input_file.exists():
                return [ErrorContent(text=f"Input file not found: {input_file}")]
            
            with tempfile.TemporaryDirectory(dir=self.settings.temp_dir) as tmpdir:
                output_file = Path(tmpdir) / f"filtered.{input_file.suffix}"
                
                cmd = [self.settings.seqkit_path, "grep"]
                
                if arguments.get("search_sequence"):
                    cmd.append("-s")
                
                if arguments.get("invert_match"):
                    cmd.append("-v")
                
                if arguments.get("ignore_case"):
                    cmd.append("-i")
                
                if arguments.get("pattern"):
                    cmd.extend(["-p", arguments["pattern"]])
                elif arguments.get("pattern_file"):
                    pattern_file = Path(arguments["pattern_file"])
                    if pattern_file.exists():
                        cmd.extend(["-f", str(pattern_file)])
                    else:
                        return [ErrorContent(text=f"Pattern file not found: {pattern_file}")]
                else:
                    return [ErrorContent(text="Either 'pattern' or 'pattern_file' must be specified")]
                
                cmd.extend(["-o", str(output_file), str(input_file)])
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    return [ErrorContent(text=f"seqkit grep failed: {stderr.decode()}")]
                
                # Get stats of filtered sequences
                stats_cmd = [self.settings.seqkit_path, "stats", "-T", str(output_file)]
                stats_process = await asyncio.create_subprocess_exec(
                    *stats_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stats_out, _ = await stats_process.communicate()
                
                return [TextContent(
                    text=f"Sequence filtering completed!\n\n"
                         f"Output file: {output_file}\n"
                         f"Pattern: {arguments.get('pattern', 'from file')}\n"
                         f"Search in sequence: {arguments.get('search_sequence', False)}\n\n"
                         f"Filtered sequences statistics:\n{stats_out.decode()}"
                )]
                
        except Exception as e:
            logger.error(f"Error in seqkit grep: {e}", exc_info=True)
            return [ErrorContent(text=f"Error: {str(e)}")]
    
    async def _run_seq(self, arguments: dict) -> list[TextContent | ErrorContent]:
        try:
            input_file = Path(arguments["input_file"])
            if not input_file.exists():
                return [ErrorContent(text=f"Input file not found: {input_file}")]
            
            with tempfile.TemporaryDirectory(dir=self.settings.temp_dir) as tmpdir:
                output_file = Path(tmpdir) / f"transformed.{input_file.suffix}"
                
                cmd = [self.settings.seqkit_path, "seq"]
                
                # Transformation options
                if arguments.get("reverse"):
                    cmd.append("-r")
                if arguments.get("complement"):
                    cmd.append("-p")
                if arguments.get("reverse_complement"):
                    cmd.append("-r")
                    cmd.append("-p")
                if arguments.get("rna2dna"):
                    cmd.append("--rna2dna")
                if arguments.get("dna2rna"):
                    cmd.append("--dna2rna")
                if arguments.get("translate"):
                    cmd.append("-t")
                
                # Length filters
                if arguments.get("min_length"):
                    cmd.extend(["-m", str(arguments["min_length"])])
                if arguments.get("max_length"):
                    cmd.extend(["-M", str(arguments["max_length"])])
                
                cmd.extend(["-o", str(output_file), str(input_file)])
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    return [ErrorContent(text=f"seqkit seq failed: {stderr.decode()}")]
                
                # Determine transformations applied
                transformations = []
                if arguments.get("reverse"):
                    transformations.append("reverse")
                if arguments.get("complement"):
                    transformations.append("complement")
                if arguments.get("reverse_complement"):
                    transformations.append("reverse complement")
                if arguments.get("rna2dna"):
                    transformations.append("RNA to DNA")
                if arguments.get("dna2rna"):
                    transformations.append("DNA to RNA")
                if arguments.get("translate"):
                    transformations.append("translate to protein")
                
                # Get output stats
                stats_cmd = [self.settings.seqkit_path, "stats", "-T", str(output_file)]
                stats_process = await asyncio.create_subprocess_exec(
                    *stats_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stats_out, _ = await stats_process.communicate()
                
                return [TextContent(
                    text=f"Sequence transformation completed!\n\n"
                         f"Output file: {output_file}\n"
                         f"Transformations: {', '.join(transformations) if transformations else 'filtering only'}\n\n"
                         f"Output statistics:\n{stats_out.decode()}"
                )]
                
        except Exception as e:
            logger.error(f"Error in seqkit seq: {e}", exc_info=True)
            return [ErrorContent(text=f"Error: {str(e)}")]
    
    async def _run_convert(self, arguments: dict) -> list[TextContent | ErrorContent]:
        try:
            input_file = Path(arguments["input_file"])
            if not input_file.exists():
                return [ErrorContent(text=f"Input file not found: {input_file}")]
            
            output_format = arguments["output_format"]
            output_ext = "fa" if output_format == "fasta" else "fq"
            
            with tempfile.TemporaryDirectory(dir=self.settings.temp_dir) as tmpdir:
                output_file = Path(tmpdir) / f"converted.{output_ext}"
                
                if output_format == "fasta":
                    cmd = [self.settings.seqkit_path, "fq2fa"]
                    if arguments.get("line_width", 0) > 0:
                        cmd.extend(["-w", str(arguments["line_width"])])
                else:  # fastq
                    cmd = [self.settings.seqkit_path, "fa2fq"]
                
                cmd.extend(["-o", str(output_file), str(input_file)])
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    return [ErrorContent(text=f"seqkit convert failed: {stderr.decode()}")]
                
                output_size = output_file.stat().st_size
                
                return [TextContent(
                    text=f"Format conversion completed!\n\n"
                         f"Input: {input_file}\n"
                         f"Output: {output_file}\n"
                         f"Output format: {output_format.upper()}\n"
                         f"Output size: {output_size:,} bytes"
                )]
                
        except Exception as e:
            logger.error(f"Error in seqkit convert: {e}", exc_info=True)
            return [ErrorContent(text=f"Error: {str(e)}")]
    
    # Implement remaining methods (_run_sort, _run_rmdup, _run_sample)...
    async def _run_sort(self, arguments: dict) -> list[TextContent | ErrorContent]:
        try:
            input_file = Path(arguments["input_file"])
            if not input_file.exists():
                return [ErrorContent(text=f"Input file not found: {input_file}")]
            
            with tempfile.TemporaryDirectory(dir=self.settings.temp_dir) as tmpdir:
                output_file = Path(tmpdir) / f"sorted.{input_file.suffix}"
                
                cmd = [self.settings.seqkit_path, "sort"]
                
                if arguments.get("by_length"):
                    cmd.append("-l")
                else:
                    sort_by = arguments.get("sort_by", "id")
                    if sort_by == "name":
                        cmd.append("-n")
                    elif sort_by == "seq":
                        cmd.append("-s")
                    elif sort_by == "length":
                        cmd.append("-l")
                
                if arguments.get("reverse"):
                    cmd.append("-r")
                
                cmd.extend(["-o", str(output_file), str(input_file)])
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    return [ErrorContent(text=f"seqkit sort failed: {stderr.decode()}")]
                
                return [TextContent(
                    text=f"Sequence sorting completed!\n\n"
                         f"Output file: {output_file}\n"
                         f"Sort criterion: {arguments.get('sort_by', 'id')}\n"
                         f"Reverse order: {arguments.get('reverse', False)}"
                )]
                
        except Exception as e:
            logger.error(f"Error in seqkit sort: {e}", exc_info=True)
            return [ErrorContent(text=f"Error: {str(e)}")]
    
    async def _run_rmdup(self, arguments: dict) -> list[TextContent | ErrorContent]:
        try:
            input_file = Path(arguments["input_file"])
            if not input_file.exists():
                return [ErrorContent(text=f"Input file not found: {input_file}")]
            
            with tempfile.TemporaryDirectory(dir=self.settings.temp_dir) as tmpdir:
                output_file = Path(tmpdir) / f"rmdup.{input_file.suffix}"
                
                cmd = [self.settings.seqkit_path, "rmdup"]
                
                if arguments.get("by_name"):
                    cmd.append("-n")
                elif arguments.get("by_seq", True):
                    cmd.append("-s")
                
                if arguments.get("ignore_case"):
                    cmd.append("-i")
                
                cmd.extend(["-o", str(output_file), str(input_file)])
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    return [ErrorContent(text=f"seqkit rmdup failed: {stderr.decode()}")]
                
                return [TextContent(
                    text=f"Duplicate removal completed!\n\n"
                         f"Output file: {output_file}\n"
                         f"Duplicates removed by: {'name' if arguments.get('by_name') else 'sequence'}"
                )]
                
        except Exception as e:
            logger.error(f"Error in seqkit rmdup: {e}", exc_info=True)
            return [ErrorContent(text=f"Error: {str(e)}")]
    
    async def _run_sample(self, arguments: dict) -> list[TextContent | ErrorContent]:
        try:
            input_file = Path(arguments["input_file"])
            if not input_file.exists():
                return [ErrorContent(text=f"Input file not found: {input_file}")]
            
            with tempfile.TemporaryDirectory(dir=self.settings.temp_dir) as tmpdir:
                output_file = Path(tmpdir) / f"sampled.{input_file.suffix}"
                
                cmd = [self.settings.seqkit_path, "sample"]
                
                if arguments.get("number"):
                    cmd.extend(["-n", str(arguments["number"])])
                elif arguments.get("proportion"):
                    cmd.extend(["-p", str(arguments["proportion"])])
                else:
                    return [ErrorContent(text="Either 'number' or 'proportion' must be specified")]
                
                if arguments.get("seed"):
                    cmd.extend(["-s", str(arguments["seed"])])
                
                cmd.extend(["-o", str(output_file), str(input_file)])
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    return [ErrorContent(text=f"seqkit sample failed: {stderr.decode()}")]
                
                return [TextContent(
                    text=f"Sequence sampling completed!\n\n"
                         f"Output file: {output_file}\n"
                         f"Sample size: {arguments.get('number', f'{arguments.get('proportion', 0)*100}%')}\n"
                         f"Seed: {arguments.get('seed', 'random')}"
                )]
                
        except Exception as e:
            logger.error(f"Error in seqkit sample: {e}", exc_info=True)
            return [ErrorContent(text=f"Error: {str(e)}")]
    
    async def run(self):
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream)


async def main():
    logging.basicConfig(level=logging.INFO)
    server = SeqKitServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())