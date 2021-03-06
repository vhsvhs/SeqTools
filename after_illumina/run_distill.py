#
# run_distill.py
#
# This is the top-level script for the ChIP-Seq Analysis Pipeline.
# This script calls functions in other Python scripts included in this project.
#

import re, os, sys, time
from annotation_db import *
from config import *
from hybrid_tools import *
from tools import *
from html_tools import *
from argParser import ArgParser
ap = ArgParser(sys.argv)

def splash():
    print "======================================================================"
    print "."
    print ". The ChIP-Seq Distillery"
    print "."
    print ". A pipeline to process your FASTQ reads."
    print "."
    print ". Last Updated: May 2016"
    print "."
    print ". This program does the following steps:"
    print "\t. Maps reads to reference genome (bowtie)"
    print "\t. Separates reads from hybrid genomes (optional)"
    print "\t. Sorts all reads and creates BAM files (samtools)"
    print "\t. Finds peaks (macs2)"
    print "\t. Calculates fold-enrichment (macs2)"
    print "\t. Compares peaks and fold-enrichments across "
    print "\t\treplicates conditions, and species."
    print ""
    print "======================================================================" 

splash()

"""read_cli reads the command-line, the annotation file, and creates a SQLite3 database."""
con = read_cli(ap)
print_settings(con)
validate_configuration_import(con)

if ap.getOptionalToggle("--load_db_only"):
    "\n. Ending"
    exit()

"""Jump allows for some steps to be skipped."""
jump = ap.getOptionalArg("--jump")
stop = ap.getOptionalArg("--stop")

if jump == False:
    jump = 0
else:
    jump = float(jump)
    
if stop == False:
    stop = 10000000
else:
    stop = float(stop)

"""Run Bowtie2 for each FASTQ path"""
if jump <= 1 and stop > 1:
    run_bowtie(con)

if jump <= 1.1 and stop > 1.1:
    check_bowtie_output(con)

if jump <= 2 and stop > 2:
    """Extract the reads from Bowtie output."""
    cur = con.cursor()
    sql = "SELECT id from Reads"
    cur.execute(sql)
    x = cur.fetchall()
    for ii in x:
        extract_matched_reads(ii[0], con)

# depricated: hybrid pairs are now mapped during when we read the configuration
# if jump <= 2.1 and stop > 2.1:
#     get_hybrid_pairs(con)

"""Remove hybrid reads that map to both parental genomes."""    
if jump <= 2.3 and stop > 2.3:
    find_hybrid_unique_reads(con)

if jump <= 2.31 and stop > 2.32:
    print_read_histograms(con)

if jump <= 2.4 and stop > 2.4:
    """Write SAM files for hybrid reads, containing only those reads that
    match the target genome <= the mismatch-threshold, and which are uniquely
    mapped to that genome."""
    write_filtered_sam(con)

if jump <= 3 and stop > 3:
    """
        Convert SAM files to sorted BAM files.
        Note: this is where the hybrid/non-hyrbid execution paths reconverge.
    """
    write_sorted_bam(con)

if jump <= 3.1 and stop > 3.1:
    """Verify the SAM -> sorted BAM occurred correctly."""
    check_bams(con, delete_sam=True)

if jump <= 3.2 and stop > 3.2:
    """"Make Bedgraphs from sorted BAMs"""
    bam2bedgraph(con)

if jump <= 3.3 and stop > 3.3:
    """Check the bedgraphs containing raw read densities (not peaks)"""
    check_bedgraphs(con)

if jump <= 4 and stop > 4:
    """Launch MACS2"""
    run_peak_calling(con)

if jump <= 4.1 and stop > 4.1:
    check_peaks(con)

if jump <= 5 and stop > 5:
    """Make BDG for FE"""
    calculate_fe(con)

if jump <= 5.1 and stop > 5.1:
    check_fe(con)

"""To-do: compare location of peaks between replicates (which presumably have the same genome)."""

if jump <= 6 and stop > 6:
    """Make WIGs from bedgraph files containing raw reads (step 3.2)
    and bedgraph files containing fold-enrichment values (step 5)"""
    bed2wig(con)

if jump <= 6.2 and stop > 6.2:
    """Checks all the wigs written in the previous step."""
    check_wig(con)

# write config
if jump <= 7 and stop > 7:
    """Write a *.config file for the apres.py script"""
    write_viz_config(con)
#
# launch the code in the folder named after_peaks:
#
vizdbpath = None
if jump <= 8 and stop > 8:
    """Launch the apres.py script."""
    vizdbpath = launch_viz(con)

print "\n. ChIP-Seq distillation is complete.  Goodbye."
exit()

