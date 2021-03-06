from Bio import SeqIO

from chipseqdb import *
from chipseqdb_api import *

from argParser import ArgParser
ap = ArgParser(sys.argv)

from plot_scatter import *

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

def read_motifs(motif_path):
    """Reads PSWM data from a text file.
    Motifs are expected to look like this:
    
    /NAME=[SWISS] ABF1 TYPE=PSFM SPECIES=S.cer
    0.208782    0.155386    0.135415    0.500414
    0.745936    0.0    0.254063    0.0
    0.0    0.0    0.0    1.0
    0.0    1.0    0.0    0.0
    
    The motif file can contain multiple motifs
    """
    if False == os.path.exists(motif_path):
        print "ERROR: I can't find the motif path:", motif_path
        exit()
    
    gene_motif = {} # key = gene name, value = list of lists, each sublist if (A,C,G,T) weights.
    
    fin = open(motif_path, "r")
    curr_motif = []
    curr_gene = None
    for line in fin.xreadlines():
        if line.startswith("#"):
            continue
        
        if line.__len__() < 3:
            continue
        
        if line.startswith("/NAME"):
            tokens = line.split()
            gene = tokens[1]
            if curr_gene != None:
                gene_motif[ curr_gene ] = curr_motif
            curr_gene = gene
            curr_motif = []
        else:
            tokens = line.split()
            if tokens.__len__() < 4:
                print "Hmmm, something is wrong with a line in the motif file. I was expecting four decimal numbers:"
                print line
                exit()
            wa = float(tokens[0])
            wc = float(tokens[1])
            wg = float(tokens[2])
            wt = float(tokens[3])
            curr_motif.append( (wa,wc,wg,wt) )
    
    gene_motif[ curr_gene ] = curr_motif
    
    return gene_motif

def build_motif_dbtables(con):
    cur = con.cursor()
    sql = "create table if not exists Motifs(id INTEGER primary key, name TEXT)"    
    cur.execute(sql)
    sql = "create table if not exists Summits2MotifScores(summitid INTEGER, motifid INTEGER, maxmotifscore FLOAT, maxmotifsite INT)"
    cur.execute(sql)
    con.commit()
    return con
    
def build_motif_table(con, motifid, motifdata):
    """motifdata is a list of lists. motifdata[site-1] = (wa,wc,wg,wt)"""
    cur = con.cursor()
    sql = "create table if not exists Motif" + motifid.__str__() + "(site INT, state TEXT, weight FLOAT)"
    cur.execute(sql)
    con.commit()

def read_genome(genome_path):
    from Bio import SeqIO
    handle = open(genome_path, "rU")
    for record in SeqIO.parse(handle, "fasta"):
        print record.id
    handle.close()
    
def score_motif_sequence(motif, seq, startsite):
    """Motif is list of lists, motif[site-1] = (wa,wc,wg,wt)
        seq is a string of nts
        startsite is the site number of the first character in seq."""
    maxsum = 0.0
    maxsumsite = 0
    motiflength = motif.__len__()
    for ii in xrange(0, seq.__len__()-motiflength ):
        sum = 0.0
        thisseq = seq[ ii: ii+motiflength ]
        for jj in xrange(0, thisseq.__len__() ):
            if seq[jj] == "A":
                sum += motif[jj][0]
            elif seq[jj] == "C":
                sum += motif[jj][1]
            elif seq[jj] == "G":
                sum += motif[jj][2]
            elif seq[jj] == "T":
                sum += motif[jj][3]
        if sum > maxsum:
            maxsum = sum
            maxsumsite = ii
    return (maxsum, maxsumsite + startsite)

def build_summits2summits(con):
    """This method fills the DB table Summits2Summits.
    It matches the location of summits across replciates, and determines which
    summits were replicated."""
    
    print "\n. Mapping summits to summits across replicates. . ."
    
    cur = con.cursor()
    sql = "delete from Summits2Summits"
    cur.execute(sql)
    con.commit()
    
    repgroupids = get_repgroup_ids(con)

    for rgroupid in repgroupids:
        rgroupid = rgroupid[0]
        groupname = get_repgroup_name(rgroupid, con)
        repids = get_repids_in_group(rgroupid, con)
        speciesid = get_speciesid_for_repid(repids[0], con)
        chromids = get_chrom_ids(con, speciesid)
        for chromid in chromids:   
            chromname = get_chrom_name(con, chromid) 
            repid_summits = {}
            
            count_inserted = 0

            for repid in repids:
                repid_summits[repid] = get_summits(con, repid, chromid)
            
            for repida in repids:
                for summita in repid_summits[ repida ]:
                    for repidb in repids:
                        if repida == repidb:
                            continue
                        for summitb in repid_summits[ repidb ]:
                            if abs(summita[3] - summitb[3]) < 30:
                                # we found two replicated summits
                                #print "found overlapping summits", summita[0], summitb[0]
                                sql = "insert or replace into Summits2Summits (summitid1, summitid2, distance)"
                                sql += " values(" + summita[0].__str__() + "," + summitb[0].__str__()
                                sql += "," + (summita[3] - summitb[3]).__str__() + ")"
                                cur.execute(sql)
                                count_inserted += 1
            print ". Found", count_inserted, "matched summits on chrom.", chromname, "in experiment", groupname
            con.commit()
                 
                    
def write_peak_motif_table(con):
    cur = con.cursor()
    
    print "\n. Writing a tables 'motifs_in_peaks.xls' for every group of replicates..."
    
    motifid_name = {}
    sql = "select id, name from Motifs"
    cur.execute(sql)
    for ii in cur.fetchall():
        motifid_name[ ii[0] ] = ii[1]
    
    repgroupids = get_repgroup_ids(con) 
    for rgroupid in repgroupids:
        rgroupid = rgroupid[0]
        groupname = get_repgroup_name(rgroupid, con)
        print ". . .", groupname
        repids = get_repids_in_group(rgroupid, con)
        repids.sort()

        for mid in motifid_name:  
            outpath = groupname + ".motifs_in_peaks." + motifid_name[ mid ] + ".xls"
            fout = open(outpath, "w")
            
            header = "Summit ID \t Motif \t Chom. \t"
            for repid in repids:
                repname = get_repname(repid, con)
                header += "MaxScore(" + repname.__str__() + ")\t"
                header += "MaxSite(" + repname.__str__() + ")\t"
                header += "MaxEnrichAtSummit(" + repname.__str__() + ")\t"
                
            fout.write(header + "\n")
            
            xvalues = [] # for the scatterplot
            yvalues = [] # for the scatterplot
                                  
            speciesid = get_speciesid_for_rep(repids[0], con)
            chromids = get_chrom_ids(con, speciesid)
            for chromid in chromids:
                chromname = get_chrom_name(con, chromid)

                summitid_data = {}
                sql = "select summitid, maxmotifscore, maxmotifsite from Summits2MotifScores where motifid=" + mid.__str__()
                sql += " and summitid in "
                sql += "(SELECT id FROM Summits where chrom=" + chromid.__str__() 
                sql += " and replicate in ("
                sql += "SELECT replicate from GroupReplicate where rgroup=" + rgroupid.__str__()
                sql += ") " 
                #sql += " and replicate=" + repids[0].__str__()
                #sql += " and (id in (select summitid1 from Summits2Summits) or id in (select summitid2 from Summits2Summits) )"
                sql += " order by site ASC)"
                cur.execute(sql)
                xx = cur.fetchall()
                if xx == None:
                    print "ERROR: I found no motif scores for sites with repgroup", groupname, "on chromosome", chromid, "for motif", mid
                    exit()
                for ii in xx:
                    summitid = ii[0]
                    summitid_data[ summitid ] = ii
                    
                    
                summitid_summitid = {}                    
                for summitida in summitid_data:
                    sql = "select summitid2 from Summits2Summits where summitid1=" + summitida.__str__()
                    cur.execute(sql)
                    xx = cur.fetchall()
                    if xx != None:
                        for ii in xx:
                            summitidb = xx[0]
                            summitid_summitid[ summitida ] = summitidb
                    sql = "select summitid1 from Summits2Summits where summitid2=" + summitida.__str__()
                    cur.execute(sql)
                    xx = cur.fetchall()
                    if xx != None:
                        for ii in xx:
                            summitidb = xx[0]
                            summitid_summitid[ summitida ] = summitidb
                
                for summitida in summitid_summitid:
                    line = summitida.__str__() + "\t"
                    line += motifid_name[mid].__str__() + "\t"
                    line += chromname + "\t"
                    line += summitid_data[summitida][1].__str__() + "\t"
                    line += summitid_data[summitida][2].__str__() + "\t" 
                    sql = "select max_enrichment from SummitsEnrichment where summit=" + summitida.__str__()
                    cur.execute(sql)
                    eval = cur.fetchone()[0]
                    line += eval.__str__() + "\t"
                    
                    xvalues.append( summitid_data[summitida][1] )
                    yvalues.append( eval )
                    
                    if summitida in summitid_summitid:
                        for summitidb in summitid_summitid[ summitida ]:
                            line += summitid_data[summitidb][1].__str__() + "\t"
                            line += summitid_data[summitidb][2].__str__() + "\t"  
                            sql = "select max_enrichment from SummitsEnrichment where summit=" + summitidb.__str__()
                            cur.execute(sql)
                            eval = cur.fetchone()[0]   
                            line += eval.__str__() + "\t"                    
                
                    fout.write(line + "\n")
            fout.close()
            
            if xvalues.__len__() != yvalues.__len__():
                print "ERROR 272: An error occurred while writing the write_peak_motif_table."
                exit()
            
            if xvalues.__len__() > 0 and yvalues.__len__() > 0:
                scatter_nxm(2, 2, [xvalues,yvalues], ["max motif score","fold-enrichment"], groupname + ".motifs_vs_fe." + motifid_name[ mid ], title="", force_square=False, plot_as_rank = [], skip_identity = False, skip_zeros = False, unit_labels=[], xlab=None, ylab=None)


##############################
#
# main
#

motifpath = ap.getArg("--motifpath")

readsdbpath = ap.getArg("--readdbpath")
rcon = lite.connect(readsdbpath, timeout=1)

vizdbpath = ap.getArg("--vizdbpath")
vcon = build_db(dbpath=vizdbpath)
vcon = build_motif_dbtables(vcon)

"""Import motifs"""
vcur = vcon.cursor()
gene_motif = read_motifs(motifpath)
motifname_id = {}
for genename in gene_motif:
    sql = "select id from Motifs where name='" + genename + "'"
    vcur.execute(sql)
    if vcur.fetchone() == None:
        sql = "insert into Motifs (name) values('" + genename + "')"
        vcur.execute(sql)
        vcon.commit()
    sql = "select id from Motifs where name='" + genename + "'"
    vcur.execute(sql)
    motifid = vcur.fetchone()[0]
    motifname_id[genename] = motifid
    build_motif_table(vcon, motifid, gene_motif[genename])
    
rcur = rcon.cursor()
speciesid_name = {}
sql = "select id, name from Species"
rcur.execute(sql)
for ii in rcur.fetchall():
    id = ii[0]
    name = ii[1]
    speciesid_name[id] = name
    
speciesid_genomepath = {}
sql = "select speciesid, genomepath from SpeciesGenomepath"
rcur.execute(sql)
for ii in rcur.fetchall():
    id = ii[0]
    genomepath = ii[1]
    sql = "select id from Species where name='" + speciesid_name[id] + "'"
    vcur.execute(sql)
    vspeciesid = vcur.fetchone()
    if vspeciesid != None:    
        speciesid_genomepath[ vspeciesid[0] ] = genomepath
        print id, genomepath, speciesid_name[id]

if jump <= 1 and stop > 1:
    
    """Parse each genome, examine all the known peaks in each chromosome,
        and then score motifs under those peaks"""
    for speciesid in speciesid_genomepath:
        genomepath = speciesid_genomepath[speciesid]
        print "\n. Scoring motifs under peaks in species", get_species_name(speciesid, vcon) 
        print "\n. Reading", genomepath
        handle = open(genomepath, "rU")
        for record in SeqIO.parse(handle, "fasta") :
            
            """Check that this chromosom exists in the viz DB"""
            sql = "select id from Chromosomes where name='" + record.name + "' and species=" + speciesid.__str__()
            vcur.execute(sql)
            fetch = vcur.fetchone()
            if fetch == None:
                print "\n. Skipping ", record.name
                continue
            else:
                chromid = fetch[0]
                
            maxchromsite = record.seq.__len__()
                
            """ Get a hold of peaks """
            sql = "select id, site from Summits where chrom=" + chromid.__str__() + " order by site ASC"
            vcur.execute(sql)
            for ii in vcur.fetchall():
                summitid = ii[0]
                summitsite = ii[1]
                lowersummitsite = summitsite - 50
                uppersummitsite = summitsite + 50
                if lowersummitsite < 50:
                    lowersummitsite = 1
                if uppersummitsite > maxchromsite:
                    uppersummitsite = maxchromsite
                summitseq = record.seq[lowersummitsite-1:uppersummitsite-1]
                
                #print "374:", speciesid, record.name, summitid, summitsite
                
                for motifname in gene_motif:            
                    (score, maxscoresite) = score_motif_sequence(gene_motif[motifname], summitseq, lowersummitsite)
                    #print "161:", speciesid, chromid, summitid, motifname, score, maxscoresite
    
                    sql = "insert or replace into Summits2MotifScores(summitid, motifid, maxmotifscore, maxmotifsite)"
                    sql += " values(" + summitid.__str__() + "," + motifname_id[motifname].__str__()
                    sql += "," + score.__str__() + "," + maxscoresite.__str__()
                    sql += ")"
                    vcur.execute(sql)
                vcon.commit()

if jump <= 1.5 and stop > 1.5:
    build_summits2summits(vcon)

if jump <= 2 and stop > 2:
    write_peak_motif_table(vcon)
    



    