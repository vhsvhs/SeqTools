from annotation_db import *

from argParser import ArgParser
ap = ArgParser(sys.argv)

def read_cli(ap):
    """Returns the database."""
    
    """In what directory do the FASTQ files exist?"""
    DATADIR = "/Network/Servers/udp015817uds.ucsf.edu/Users/eugeniom/Documents/ChIP-seq_analysis/Ndt80/"
    x = ap.getOptionalArg("--datadir")
    if x != False:
        DATADIR = x
    
    """In what directory should output be written?"""
    OUTDIR = "./"
    x = ap.getOptionalArg("--outdir")
    if x != False:
        OUTDIR = x
    
    """Path to annotation file, describining FASTQ files."""
    APATH = "mancera_chipseq_sample_annotation.txt"
    x = ap.getOptionalArg("--annopath")
    if x != False:
        APATH = x
    DBPATH = ap.getOptionalArg("--dbpath")
    if DBPATH == False:
        DBPATH = APATH + ".db"

    GENOME_LIST = "genome_list.txt"
    x = ap.getOptionalArg("--genome_list")
    if x != False:
        GENOME_LIST = x
        
    PROJECT_NAME = ap.getArg("--project_name")
    
    """Software Paths:"""
    BOWTIE2 = "bowtie2"
    x = ap.getOptionalArg("--bowtie2")
    if x != False:
        BOWTIE2 = x
    
    SAMTOOLS = "samtools"
    x = ap.getOptionalArg("--samtools")
    if x != False:
        SAMTOOLS = x
    
    USE_MPI = 0
    x = ap.getOptionalArg("--use_mpi")
    if x != False:
        USE_MPI = 1
    
    MPIRUN = "mpirun -np 4 /common/bin/mpi_dispatch"
    
    MACS2 = "/common/REPOSITORY/MACS2-2.0.10.07132012/bin/macs2"
    x = ap.getOptionalArg("--macs2")
    if x != False:
        MACS2 = x

    GENOME_COVERAGE_BED = "/common/REPOSITORY/bedtools2/bin/genomeCoverageBed"
    x = ap.getOptionalArg("--gcb")
    if x != False:
        GENOME_COVERAGE_BED = x
    
    SEQTOOLSDIR = "~/Applications/SeqTools"
    x = ap.getOptionalArg("--seqtoolsdir")
    if x != False:
        SEQTOOLSDIR = x
    
    """The pillars file provides alias names for orthologous genes in different species.
    For example, a pillars file for several model yeast species can be downloaded from the Candida Genome Database.
    This information is used later in the script apres.py"""
    PILLARSPATH = "/Network/Servers/udp015817uds.ucsf.edu/Users/Shared/sequencing_analysis/Pillars.tab.txt"
    x = ap.getOptionalArg("--pillarspath")
    if x != False:
        PILLARSPATH = x
        
    """restricts analysis to only those annotation lines whose sample column is this value."""
    restrict_to_sample = ap.getOptionalArg("--restrict_to_sample")
    
    """restrics the analysis to only those annotations whose 'strain' column has a value matching something in this list."""
    restrict_to_strain = ap.getOptionalList("--restrict_to_strain")
    
    PRACTICE_MODE = ap.getOptionalToggle("--practice_mode")
    
    MISMATCH_THRESHOLD = -1
    x = ap.getOptionalArg("--mismatch_thresh")
    if x != False:
        MISMATCH_THRESHOLD = int(x)
    
    """Build or restore the DB"""
    con = get_db(DBPATH)
    cur = con.cursor()
    
    sql = "delete from Settings"
    cur.execute(sql)
    con.commit()
    
    """Write all the settings into the DB.
    Later in the program, lookups of settings will use the values in the DB, 
    rather than the values in the ArgParser object."""
    sql = "insert or replace into Settings (keyword, value) VALUES('bowtie2','" + BOWTIE2 + "')"
    cur.execute(sql)
    sql = "insert or replace into Settings (keyword, value) VALUES('datadir','" + DATADIR + "')"
    cur.execute(sql)
    sql = "insert or replace into Settings (keyword, value) VALUES('outdir','" + OUTDIR + "')"
    cur.execute(sql)
    sql = "insert or replace into Settings (keyword, value) VALUES('samtools','" + SAMTOOLS + "')"
    cur.execute(sql)
    sql = "insert or replace into Settings (keyword, value) VALUES('macs2','" + MACS2 + "')"
    cur.execute(sql)
    sql = "insert or replace into Settings (keyword, value) VALUES('gcb','" + GENOME_COVERAGE_BED + "')"
    cur.execute(sql)
    sql = "insert or replace into Settings (keyword, value) VALUES('seqtoolsdir','" + SEQTOOLSDIR + "')"
    cur.execute(sql)
    sql = "insert or replace into Settings (keyword, value) VALUES('genome_list','" + GENOME_LIST + "')"
    cur.execute(sql)
    sql = "insert or replace into Settings (keyword, value) VALUES('use_mpi','" + USE_MPI.__str__() + "')"
    cur.execute(sql)
    sql = "insert or replace into Settings (keyword, value) VALUES('mpirun','" + MPIRUN + "')"
    cur.execute(sql)
    sql = "insert or replace into Settings (keyword, value) VALUES('mismatch_thresh','" + MISMATCH_THRESHOLD.__str__() + "')"
    cur.execute(sql)
    if restrict_to_sample != False:
        sql = "insert or replace into Settings (keyword, value) VALUES('restrict_to_sample','" + restrict_to_sample + "')"
        cur.execute(sql)
    for strain in restrict_to_strain:
        sql = "insert into Settings (keyword, value) VALUES('restrict_to_strain','" + strain + "')"
        cur.execute(sql)        
    sql = "insert or replace into Settings (keyword, value) VALUES('project_name','" + PROJECT_NAME + "')"
    cur.execute(sql)
    sql = "insert or replace into Settings (keyword, value) VALUES('pillars_path','" + PILLARSPATH + "')"
    cur.execute(sql)
    
    """chrom_filter will restrict the analysis to only those reads whose chromosome name contains the value of --chrom_filter"""
    chrom_filters = ap.getOptionalList("--chrom_filter")
    for cf in chrom_filters:
        sql = "insert or replace into Settings (keyword, value) VALUES('chrom_filter','" + cf + "')"
        cur.execute(sql)

    """If practice mode is enabled, then major programs will not be launched, such as Bowtie, MACS2, etc.
    However, regardless of practice mode, shell scripts for these programs will be written.
    Essentially, practice mode provides a means to test if the pipeline will succeed."""
    x = 0
    if PRACTICE_MODE:
        print "\n. Practice Mode Enabled."
        x = 1
    sql = "insert or replace into Settings (keyword, value) VALUES('practice_mode','" + x.__str__() + "')"
    cur.execute(sql)
    con.commit()
    
    con = import_genome_list(GENOME_LIST, con)
    
    con = import_annotations(APATH, con)
    return con

def print_settings(con):
    cur = con.cursor()
    sql = "select keyword, value from Settings"
    cur.execute(sql)
    x = cur.fetchall()
    if x.__len__() == 0:
        print "\n. Warning 139 - The Settings table is empty."
    print "\n. Current Settings:"
    for ii in x:
        print "\t", ii[0], ":", ii[1]
    return