---
title:  Dropout and Regularization
author: Akshay Badola
date: 2018-07-04
bibliography: ./all.bib
link-citations: true
mathjax: ./settings/MathJax
keywords: regularization, dropout, deep learning, neural networks, machine learning
category: research
tags: dropout, regularization, machine learning, neural networks
---

<!--includes settings/template/latex.template-->


`<h1 align="center">Dropout and Regularization</h1>`{=html}

## Dropout

First mention of dropout is found in [@hinton2012improving]. That
paper talks about preventing feature correlation in neural
networks. Dropout was applied successfully in 
[@krizhevsky2012imagenet] after which it gained widespread
popularity. It was shown to be effective in Recurrent Neural Networks
for the first time in [@zaremba2014recurrent]. 

### Biological and Historical Context

Historically, neural network pruning was an effective way to prevent
overfitting of neural networks [@lecun1990optimal;
@hassibi1993second]. These methods used ideas from perturbation theory
to minimize the change in second order gradients (hessian).

Biological motivation for dropout and other sparsity inducing methods
can be found in the human brain development
[@paradiso2007neuroscience, pp. 704-707]. The process is known as
_programmed cell death_.

There are theories and evidence for correlation between sparsity in
the brain and intelligence or expertise [@hanggi2014architecture;
brogliato2014sparse; @gencc2018diffusion]

### Dropout for Regularization in Deep Neural Networks

A decent introduction to Regularization Theory can be found in [Haykin
@haykin2009neural, ch. 7]. A tutorial with more linear algebraic
formulation instead of function analytic perspective is
[@neumaier1998solving]. A thorough introduction to the general theory
of regularization can be found in [@engl1996regularization].  A simpler
approach to regularization in terms controlling controlling the
curvature can be seen in the theory of Additive Models. A good
introductory text for that is [@wood2006generalized].

The paper that we had discussed was [@wang2013fast]. Equivalence of
dropout to $L_2$ regularization can be seen in
[@srivastava2014dropout]. As we'd discussed, all norm penalties are
some form of Tikhonov Regularization.

[@wang2013fast] used the Gaussian approximation to the Bernoulli
distribution to analytically find the $\Delta w$ and thereby speeding
up the process. However, in practice their method doesn't scale well
to deeper networks. Gal and Gahramani [@gal2015dropout] have developed
a sounder model with a Gaussian Process approximation. I'll try to
read that soon.

### Noise and Regularization

Addition of noise to input data was proven equivalent to Tikhonov
regularization by Bishop in [@bishop1995training]. An interesting
article that adds noise to gradients is
[@neelakantan2015adding]. Similar perturbation at the local minima has
been a common technique to find solutions of problems with greedy
methods.

### Random Projections and Subspace Search

Random subspace search isn't usually seen as a similar method as it is
more a feature selection method, but that too is an effective
regularizer. First discussed in [@ho1998random] it discusses building
an ensemble of decision trees over subsets of features. The method was
combined with _bootstrap_ and _bagging_ to create Random Forests by
Breiman later [@breiman2001random]

$\mathcal{N}(\mu, \sigma) = \frac{1}{{2\pi\sigma}^{d/2}}\exp(\mathbf{(x-\mu)^T\Sigma^{-1}(x-\mu)})$

Since for dropout the equation over a vector and corresponding weights
reduces to $\sum p_i x_i w_i$, it can be seen as either zeroing out
$x_i$ with probability $p_i$ drawn from a Bernoulli distribution, or
$w$. A relation to random subspace methods is arrived at immediately.

Random projections [@candes2006near] is a different idea which sounds
similar but on which further reading is required.

# References
