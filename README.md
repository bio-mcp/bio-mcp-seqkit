# bio-mcp-seqkit

MCP (Model Context Protocol) server for SeqKit, a cross-platform and ultrafast toolkit for FASTA/Q file manipulation.

## Overview

This MCP server provides access to various SeqKit functionalities, enabling AI assistants to perform common tasks like getting statistics, extracting subsequences, searching, transforming, sorting, removing duplicates, sampling, and converting sequence files.

## Features

- **seqkit_stats**: Get basic statistics of FASTA/FASTQ files.
- **seqkit_subseq**: Extract subsequences by region or BED file.
- **seqkit_grep**: Search sequences by pattern or ID.
- **seqkit_seq**: Transform sequences (reverse, complement, translate, etc.) and filter by length.
- **seqkit_sort**: Sort sequences by different criteria (ID, name, sequence, length).
- **seqkit_rmdup**: Remove duplicate sequences.
- **seqkit_sample**: Sample sequences randomly by number or proportion.
- **seqkit_convert**: Convert between FASTA and FASTQ formats.

## Installation

### Prerequisites

- Python 3.9+
- SeqKit installed (`seqkit`)

### Install SeqKit

```bash
# Download from GitHub releases (example for Linux AMD64)
wget https://github.com/shenwei356/seqkit/releases/latest/download/seqkit_linux_amd64.tar.gz
tar -xzf seqkit_linux_amd64.tar.gz
sudo mv seqkit /usr/local/bin/

# From conda
conda install -c bioconda seqkit
```

### Install the MCP server

```bash
git clone https://github.com/bio-mcp/bio-mcp-seqkit
cd bio-mcp-seqkit
pip install -e .
```

## Configuration

Add to your MCP client configuration (e.g., Claude Desktop `~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "bio-seqkit": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/bio-mcp-seqkit"
    }
  }
}
```

### Environment Variables

- `BIO_MCP_MAX_FILE_SIZE`: Maximum input file size in bytes (default: 10GB)
- `BIO_MCP_TIMEOUT`: Command timeout in seconds (default: 600)
- `BIO_MCP_SEQKIT_PATH`: Path to SeqKit executable (default: finds in PATH)
- `BIO_MCP_TEMP_DIR`: Temporary directory for processing

## Usage

Once configured, the AI assistant can use the following tools:

### `seqkit_stats` - Get Sequence Statistics

Get basic statistics of FASTA/FASTQ files.

**Parameters:**
- `input_file` (required): Path to FASTA/FASTQ file.
- `all_stats`: Show all statistics including N50 (boolean).

### `seqkit_subseq` - Extract Subsequences

Extract subsequences by region or from a BED file.

**Parameters:**
- `input_file` (required): Path to FASTA/FASTQ file.
- `region`: Region to extract (e.g., `1:100-200` or `chr1:1000-2000`).
- `bed_file`: BED file with regions to extract.

### `seqkit_grep` - Search Sequences

Search sequences by pattern or ID.

**Parameters:**
- `input_file` (required): Path to FASTA/FASTQ file.
- `pattern`: Search pattern (regex supported).
- `pattern_file`: File with list of patterns/IDs.
- `search_sequence`: Search in sequence instead of header (boolean).
- `invert_match`: Invert match (exclude matching sequences) (boolean).
- `ignore_case`: Ignore case (boolean).

### `seqkit_seq` - Transform Sequences

Transform sequences (reverse, complement, translate, etc.) and filter by length.

**Parameters:**
- `input_file` (required): Path to FASTA/FASTQ file.
- `reverse`: Reverse sequence (boolean).
- `complement`: Complement sequence (boolean).
- `reverse_complement`: Reverse complement sequence (boolean).
- `rna2dna`: Convert RNA to DNA (boolean).
- `dna2rna`: Convert DNA to RNA (boolean).
- `translate`: Translate to protein (boolean).
- `min_length`: Minimum sequence length filter (integer).
- `max_length`: Maximum sequence length filter (integer).

### `seqkit_sort` - Sort Sequences

Sort sequences by different criteria.

**Parameters:**
- `input_file` (required): Path to FASTA/FASTQ file.
- `sort_by`: Sort criterion (`id`, `name`, `seq`, or `length`). Default: `id`.
- `reverse`: Reverse sort order (boolean).
- `by_length`: Sort by sequence length (boolean).

### `seqkit_rmdup` - Remove Duplicate Sequences

Remove duplicate sequences.

**Parameters:**
- `input_file` (required): Path to FASTA/FASTQ file.
- `by_name`: Remove duplicates by sequence name (boolean).
- `by_seq`: Remove duplicates by sequence (boolean). Default: `True`.
- `ignore_case`: Ignore case when comparing (boolean).

### `seqkit_sample` - Sample Sequences

Sample sequences randomly by number or proportion.

**Parameters:**
- `input_file` (required): Path to FASTA/FASTQ file.
- `number`: Number of sequences to sample (integer).
- `proportion`: Proportion of sequences to sample (0-1) (float).
- `seed`: Random seed for reproducible sampling (integer).

### `seqkit_convert` - Convert Formats

Convert between FASTA and FASTQ formats.

**Parameters:**
- `input_file` (required): Path to input file.
- `output_format` (required): Output format (`fasta` or `fastq`).
- `line_width`: Line width for FASTA output (0 for no wrapping) (integer). Default: `0`.

## Examples

### Get statistics for a FASTQ file
```
Get detailed statistics for my_reads.fastq, including N50.
```

### Extract a subsequence
```
Extract the subsequence from chr1:100-200 in reference.fasta.
```

### Translate DNA to protein
```
Translate the DNA sequences in coding_sequences.fasta to protein.
```

## Development

### Running tests

```bash
pytest tests/
```

### Building Docker image

```bash
docker build -t bio-mcp-seqkit .
```

## License

MIT License
