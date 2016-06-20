import addpath
from collections import defaultdict
from sklearn.cluster import KMeans
import itertools
import numpy as np
import matplotlib.pyplot as plt
import pickle
import sys
import pandas as pd
import scipy as sp
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import scale
from src.representation import Representation


def export_clusters(cluster_labels, gene_set,
                    savename='../out/clustered_genes.p'):
    num_clusters = np.bincount(cluster_labels).size
    cluster_dict = {}
    for i in range(num_clusters):
        cluster_label = 'c' + str(i)
        if cluster_dict.get(cluster_label) is None:
            genes = gene_set[np.where(cluster_labels == i)[0]]
            cluster_dict[cluster_label] = genes

    pickle.dump(cluster_dict, open(savename, 'w'))
    # sio.savemat(savename, cluster_dict)


def plot_2D(data, color_labels=None, x=0, y=1, xlabel='X', ylabel='Y', title='2-Dimensional Plot', savename='plot'):
    fig = plt.figure()
    x_vals = data[:, x]
    y_vals = data[:, y]
    colors = label_coloring(color_labels)
    if colors is not None:
        plt.scatter(x_vals, y_vals, figure=fig, s=50, c=colors)
    else:
        plt.scatter(x_vals, y_vals, figure=fig, s=50)

    plt.title(title, figure=fig)
    plt.xlabel(xlabel, figure=fig)
    plt.ylabel(ylabel, figure=fig)
    savename = savename + title
    plt.savefig(savename)
    plt.close()
    return

def PCPlot(data, pc1=0, pc2=1, k=3, xlabel='PC-1', ylabel='PC-2', title='PC-Plot', savename='plot'):
    """
    Plot over PCs (1st and 2nd) coloring based on kmeans clustering
    """
    pca = Representation(data, 'pca').getRepresentation()
    kmeans = KMeans(n_clusters=k)
    kmeans.fit(data)
    fig = plt.figure()
    plt.title(title, figure=fig)

    ax1 = fig.add_subplot(211)
    x_vals = pca[0][:, pc1]
    y_vals = pca[0][:, pc2]
    colors = label_coloring(kmeans.labels_)
    if colors is not None:
        ax1.scatter(x_vals, y_vals, s=50, c=colors)
    else:
        ax1.scatter(x_vals, y_vals, s=50)

    # ax1.title(plttitle)
    ax1.set_xlabel(xlabel)
    ax1.set_ylabel(ylabel)

    ax2 = fig.add_subplot(212)
    ax2.plot(pca[2])
    ax2.set_xlabel('PC')
    ax2.set_ylabel('Explained Variance Ratio')

    savename = savename + title
    plt.savefig(savename)
    plt.close()
    return

def QQPlot(observed_p, savename):
    # make the QQ plot, borrowed from Princy's code demonstrating QQ plots
    n = observed_p.size
    obs_p = -np.log10(np.sort(observed_p))
    th_p = np.arange(1/float(n), 1+(1/float(n)), 1/float(n))
    th_p = -np.log10(th_p)
    fig, ax = plt.subplots(ncols=1)
    ax.scatter(th_p, obs_p)
    x = np.linspace(*ax.get_xlim())
    ax.plot(x, x)
    ax.set_xlabel('Theoretical')
    ax.set_ylabel('Observed')
    ax.set_title(savename)
    plt.savefig(savename)
    plt.close()


def benjamini(x, p):
    x = np.sort(x.flatten())
    p = p / x.size
    significant = np.empty(x.size, dtype=bool)
    for i in range(x.size):
        significant[i] = x[i] < (i+1) * p
    return significant


def label_coloring(labels):
    """
    returns a coloring where each unique label gets its own color
    """
    if labels is None:
        return None
    num_colors = np.bincount(labels).size
    color_vals = np.linspace(0, 1, num_colors, endpoint=True)
    color = np.empty(labels.size)
    for i in range(0, num_colors):
        color[labels == i] = color_vals[i]
    return color


def get_lsv(X, pca):
    """
    make sure mean of a feature across samples is 0
    """
    n = pca.explained_variance_.size

    # matrix of singular values
    SV = np.zeros((n, n))
    SV[np.diag_indices(n)] = pca.explained_variance_
    SV = np.sqrt(SV)

    # X = U SV W.T, where the columns of W are are eigenvectors/PCs
    # since rows of pca.components_ are PCs pca.components_ = W.T
    W = pca.components_.T
    # U = X W SV^-1, since W W.T = I
    U = X.dot(W).dot(np.linalg.inv(SV))
    return U, SV, W


def regress_out(self, ind, X=None, axis=None):
    if X is None:
        X = self.X
    if axis is None:
        # try and figure out what axis based on the
        # dimensions of independent variable
        n = ind.shape[0]
        if X.shape[0] == X.shape[1]:
            # this is an ambigous case
            print >> sys.stderr, 'Ambiguous dimensions, please specify axis'
            return
        if X.shape[0] == n:
            axis = 0
        elif X.shape[1] == n:
            axis = 1
        else:
            print >> sys.stderr, 'Mismatched dimensions'

    print 'Axis: ', axis
    if axis == 1:
        X = np.transpose(X)
    linreg = LinearRegression()
    linreg.fit(ind, X)
    new_data = X - linreg.predict(ind)
    # add back the intercept
    new_data = np.apply_along_axis(np.add, 1, new_data, linreg.intercept_)
    if axis == 1:
        X = np.transpose(X)
        new_data = np.transpose(new_data)
    return new_data, linreg


def associate(data1, data2, targets1=None, targets2=None, outpath=''):
    """
    data1 (ixj)and data2(nxm) are DataFrames
    targets are the columns of data 2 that we want to check an
    associationg for with the rows of data1
    returns an ixm dataframe with benjamini hochberg corrected p values of
    spearman correlations
    """
    print 'Finding Associations...'
    if targets1 is None:
        targets1 = data1.axes[0]
    if targets2 is None:
        targets2 = data2.axes[1]

    output = pd.DataFrame(data=np.empty((targets1.size, targets2.size)),
                          index=targets1, columns=targets2)

    for j in targets2:
        for i in targets1:
            notnan = data2[(~np.isnan(data2[j].astype(float)))].index
            r, p = sp.stats.spearmanr(data1.loc[i, notnan].as_matrix(),
                                      data2.loc[notnan, j].as_matrix())
            output.loc[i, j] = p
        savepath = outpath+j
        QQPlot(output[j].as_matrix(), savename=savepath)

    return output


def check_k_range(data, cluster_sizes, iterations, savename):
    for k in cluster_sizes:
        print 'k= :', k
        index_pairs = defaultdict(int)
        conservation = []
        for repeat in range(iterations):
            km = KMeans(n_clusters=k)
            km.fit(data)
            l = km.labels_
            for i in range(k):
                pairs = set(itertools.combinations(np.where(l == i)[0].tolist(), 2))
                for pair in pairs:
                    index_pairs.__getitem__(pair)
                    index_pairs[pair] += 1
        conserved = sum(index_pairs.values()) / float((len(index_pairs.keys()) * 2))
        print conserved
        conservation.append(conserved)

    pickle.dump(open(savename, 'wb'))
    print conservation


def iterative_clean(p, clean_components, clusters=3, transpose=False,
                    odir='./'):
    """
    p is a preprocessing object,
    clean components is the number of PCs we want to remove
    clusters is the number of clusters to label datapoints on PC plot with
    scales the data before runnning it through PCPlot
    """
    for i in range(clean_components+1):
        c = np.arange(i)
        print 'Cleaning PCs: ', c
        clean = p.clean(components=c, update_data=False)
        if transpose:
            clean = clean.T
        clean = scale(clean)

        plt_title = "RemovedPCs:" + str(c)
        PCPlot(clean, k=3, xlabel='PC-1', ylabel='PC-2', title=plt_title, savename=odir)
        #pca = Representation(clean, 'pca').getRepresentation()
        #kmeans = KMeans(n_clusters=clusters)
        #kmeans.fit(clean)

        #plot_2D(pca[0], kmeans.labels_, title=plt_title, savename=odir)
