"""
Evaluation metrics for hierarchical classification.

"""
from contextlib import contextmanager

import numpy as np
from networkx import all_pairs_shortest_path_length, relabel_nodes
from sklearn.preprocessing import MultiLabelBinarizer

from sklearn_hierarchical_classification.constants import ROOT


@contextmanager
def multi_labeled(y_true, y_pred, graph):
    """
    Helper context manager for using the hierarchical evaluation metrics
    defined in this model.

    Briefly, the evaluation metrics expect data in a binarized multi-label format,
    the same as returned when using scikit-learn's MultiLabelBinarizer.

    This method therefore encapsulate the boilerplate required to fit such a
    label transformation on the data we wish to evaluate (y_true, y_pred) as well as
    applying it to the class hierarchy itself (graph), by relabeling the nodes.

    See the examples/classify_digits.py file for example usage.

    Parameters
    ----------
    y_true : array-like, shape = [n_samples, 1].
        ground truth targets

    y_pred : array-like, shape = [n_samples, 1].
        predicted targets

    graph : the class hierarchy graph, given as a `networkx.DiGraph` instance

    Returns
    -------
    y_true_ : array-like, shape = [n_samples, n_classes].
        ground truth targets, transformed to a binary multi-label matrix format.
    y_pred_ : array-like, shape = [n_samples, n_classes].
        predicted targets, transformed to a binary multi-label matrix format.
    graph : the class hierarchy graph, given as a `networkx.DiGraph` instance,
        transformed to use the (integer) IDs fitted by the multi label binarizer.

    """
    mlb = MultiLabelBinarizer()
    mlb.fit(
        node
        for node in graph.nodes
        if node != ROOT
    )

    node_label_mapping = {
        old_label: new_label
        for new_label, old_label in enumerate(list(mlb.classes_))
    }

    yield (
        mlb.transform(y_true),
        mlb.transform(y_pred),
        relabel_nodes(graph, node_label_mapping),
    )


def fill_ancestors(y, graph, copy=True):
    """
    Compute the full ancestor set for y given as a matrix of 0-1.

    Each row will be processed and filled in with 1s in indexes corresponding
    to the (integer) id of the ancestor nodes of those already marked with 1
    in that row, based on the given class hierarchy graph.

    Parameters
    ----------
    y : array-like, shape = [n_samples, n_classes].
        multi-class targets, corresponding to graph node integer ids.

    graph : the class hierarchy graph, given as a `networkx.DiGraph` instance

    Returns
    -------
    y_ : array-like, shape = [n_samples, n_classes].
        multi-class targets, corresponding to graph node integer ids with
        all ancestors of existing labels in matrix filled in, per row.

    """
    y_ = y.copy() if copy else y
    paths = all_pairs_shortest_path_length(graph.reverse(copy=False))
    for target, distances in paths:
        if target == ROOT:
            # Our stub ROOT node, can skip
            continue

        ix_rows = np.where(y[:, target] > 0)[0]
        # all ancestors, except the last one which would be the ROOT node
        ancestors = list(distances.keys())[:-1]
        y_[tuple(np.meshgrid(ix_rows, ancestors))] = 1
    graph.reverse(copy=False)
    return y_


def h_precision_score(y_true, y_pred, class_hierarchy):
    """
    Calculate the hierarchical precision ("hR") metric based on
    given set of true class labels and predicated class labels, and the
    class hierarchy graph.

    Note that the format expected here for `y_true` and `y_pred` is a
    binary multi-label matrix format, e.g. as can be generated by scikit-learn's
    MultiLabelBinarizer.

    For motivation and definition details, see:

        Functional Annotation of Genes Using Hierarchical Text
        Categorization, Kiritchenko et al 2008

        http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.68.5824&rep=rep1&type=pdf

    Parameters
    ----------
    y_true : array-like, shape = [n_samples, n_classes].
        Ground truth multi-class targets.

    y_pred : array-like, shape = [n_samples, n_classes].
        Predicted multi-class targets.

    class_hierarchy : the class hierarchy graph, given as a `networkx.DiGraph` instance
        Node ids must be integer and correspond to the indices into the y_true / y_pred matrices.

    Returns
    -------
    hP : float
        The computed hierarchical precision score.

    """
    y_true_ = fill_ancestors(y_true, graph=class_hierarchy)
    y_pred_ = fill_ancestors(y_pred, graph=class_hierarchy)

    ix = np.where((y_true_ != 0) & (y_pred_ != 0))

    true_positives = len(ix[0])
    all_results = np.count_nonzero(y_pred_)

    return true_positives / all_results


def h_recall_score(y_true, y_pred, class_hierarchy):
    """
    Calculate the hierarchical recall ("hR") metric based on
    given set of true class labels and predicated class labels, and the
    class hierarchy graph.

    Note that the format expected here for `y_true` and `y_pred` is a
    binary multi-label matrix format, e.g. as can be generated by scikit-learn's
    MultiLabelBinarizer.

    For motivation and definition details, see:

        Functional Annotation of Genes Using Hierarchical Text
        Categorization, Kiritchenko et al 2008

        http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.68.5824&rep=rep1&type=pdf

    Parameters
    ----------
    y_true : array-like, shape = [n_samples, n_classes].
        Ground truth multi-class targets.

    y_pred : array-like, shape = [n_samples, n_classes].
        Predicted multi-class targets.

    class_hierarchy : the class hierarchy graph, given as a `networkx.DiGraph` instance.
        Node ids must be integer and correspond to the indices into the y_true / y_pred matrices.

    Returns
    -------
    hR : float
        The computed hierarchical recall score.

    """
    y_true_ = fill_ancestors(y_true, graph=class_hierarchy)
    y_pred_ = fill_ancestors(y_pred, graph=class_hierarchy)

    ix = np.where((y_true_ != 0) & (y_pred_ != 0))

    true_positives = len(ix[0])
    all_positives = np.count_nonzero(y_true_)

    return true_positives / all_positives


def h_fbeta_score(y_true, y_pred, class_hierarchy, beta=1.):
    """
    Calculate the hierarchical F-beta ("hF_{\beta}") metric based on
    given set of true class labels and predicated class labels, and the
    class hierarchy graph.

    Note that the format expected here for `y_true` and `y_pred` is a
    binary multi-label matrix format, e.g. as can be generated by scikit-learn's
    MultiLabelBinarizer.

    For motivation and definition details, see:

        Functional Annotation of Genes Using Hierarchical Text
        Categorization, Kiritchenko et al 2008

        http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.68.5824&rep=rep1&type=pdf

    Parameters
    ----------
    y_true : array-like, shape = [n_samples, n_classes].
        Ground truth multi-class targets.

    y_pred : array-like, shape = [n_samples, n_classes].
        Predicted multi-class targets.

    class_hierarchy : the class hierarchy graph, given as a `networkx.DiGraph` instance
        Node ids must be integer and correspond to the indices into the y_true / y_pred matrices.

    beta: float
        the beta parameter for the F-beta score. Defaults to F1 score (beta=1).

    Returns
    -------
    hFscore : float
        The computed hierarchical F-score.

    """
    hP = h_precision_score(y_true, y_pred, class_hierarchy)
    hR = h_recall_score(y_true, y_pred, class_hierarchy)
    return (1. + beta ** 2.) * hP * hR / (beta ** 2. * hP + hR)
