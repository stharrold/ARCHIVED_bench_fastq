#!/usr/bin/env bash
# Script for testing compression.
# Note: Requires root access since operated on disk mounted to virtual instance.
# TODO: read in a user-defined list of funcitons with options.
# TODO: read in a user-defined list of files.
# TODO: rewrite script in python to add easy logging.

# Read in user input and check for .fastq.gz files.
for fastqgz in "$@"
do
    if [[ ${fastqgz: -9} == '.fastq.gz' ]]
    then
	# Make backup copy of original .fastq.gz to restore after compress/decompress cycle.
	# Make backup copy of original .fastq to compare with decompressed file.
	# (Comparing .fastq files mainly a concern for .fastq-specific compression.)
	echo
	echo "Begin processing:" $fastqgz
	date
	echo "Backing up original .fastq.gz, .fastq files."
	date
	fastqgz_orig=$fastqgz\_ORIGINAL
	sudo cp $fastqgz $fastqgz_orig
	sudo gunzip $fastqgz
	fastq=${fastqgz%.gz}
	fastq_orig=$fastq\_ORIGINAL
	sudo cp $fastq $fastq_orig
	echo "Intial .fastq size:"
	date
	du --bytes $fastq $fastq_orig
	echo "Begin benchmark compression tests."
	date
	iter=0
	while [ $iter -lt 2 ]
	do
	    # Test compression methods for execution time and file size.
	    # Diff fails due to file size.
	    # Direct commands to stdout as a record.
	    echo "Iteration:" $iter
	    date
	    set -x
	    # Test gzip.
	    echo "Testing gzip:"
	    date
	    sudo time gzip -v --fast $fastq
	    du --bytes $fastq\.gz
	    sudo time gunzip -v $fastq\.gz
	    du --bytes $fastq
	    # sudo diff --speed-large-files --report-identical-files $fastq $fastq_orig | head --lines=100
	    # Test bzip2.
	    echo "Testing bzip2:"
	    date
	    sudo time bzip2 -v --fast $fastq
	    du --bytes $fastq\.bz2
	    sudo time bunzip2 -v $fastq\.bz2
	    du --bytes $fastq
	    # sudo diff --speed-large-files --report-identical-files $fastq $fastq_orig | head --lines=100
	    # Test fqz_comp.
	    # fqz_comp doesn't automatically remove old decompressed/compressed files. Do manually.
	    echo "Testing fqz_comp:"
	    date
	    sudo time fqz_comp $fastq $fastq\.fqz
	    du --bytes $fastq\.fqz
	    sudo rm $fastq
	    sudo time fqz_comp -d $fastq\.fqz $fastq
	    du --bytes $fastq
	    sudo rm $fastq\.fqz
	    # sudo diff --speed-large-files --report-identical-files $fastq $fastq_orig | head --lines=100
	    # Test quip.
	    # quip doesn't automatically remove old decompressed/compressed files. Do manually.
	    echo "Testing quip:"
	    date
	    sudo time quip $fastq
	    du --bytes $fastq\.qp
	    sudo rm $fastq
	    sudo time unquip $fastq\.qp
	    du --bytes $fastq
	    sudo rm $fastq\.qp
	    # sudo diff --speed-large-files --report-identical-files $fastq $fastq_orig | head --lines=100
	    set +x
	    iter=$[$iter+1]
	done
	echo "End benchmark compression tests."
	date
	echo "Restoring original .fastq.gz file."
	date
	sudo rm $fastq $fastq_orig
	sudo mv $fastqgz_orig $fastqgz
	echo "End processing:" $fastqgz
	date
    fi
done
