# alg = sys.argv[1]
# m = int(sys.argv[2])
# k = int(sys.argv[3])
# state_range = [int(i) for i in sys.argv[4:]]
# k_range = [25, 50, 75, 100, 125]
# state_range = [10, 20, 40, 60]
cd /home/ktayeb1/disease-time-series/hmm
python random_init.py viterbi 6000 25 10 20 40 60
python random_init.py viterbi 6000 75 10 20 40 60
python random_init.py viterbi 6000 125 10 20 40 60