import tensorflow as tf
import math
import numpy as np
import pyredner_tensorflow as pyredner

####################### Spherical Harmonics utilities ########################
# Code adapted from "Spherical Harmonic Lighting: The Gritty Details", Robin Green
# http://silviojemma.com/public/papers/lighting/spherical-harmonic-lighting.pdf
def associated_legendre_polynomial(l, m, x):
    pmm = tf.convert_to_tensor(np.ones_like(x), dtype=tf.float32)
    if m > 0:
        somx2 = tf.sqrt((1 - x) * (1 + x))
        fact = 1.0
        for i in range(1, m + 1):
            pmm = pmm * (-fact) * somx2
            fact += 2.0
    if l == m:
        return pmm
    pmmp1 = x * (2.0 * m + 1.0) * pmm
    if l == m + 1:
        return pmmp1
    pll = tf.convert_to_tensor(np.zeros_like(x), dtype=tf.float32)
    for ll in range(m + 2, l + 1):
        pll = ((2.0 * ll - 1.0) * x * pmmp1 - (ll + m - 1.0) * pmm) / (ll - m)
        pmm = pmmp1
        pmmp1 = pll
    return pll

def SH_renormalization(l, m):
    return math.sqrt((2.0 * l + 1.0) * math.factorial(l - m) / \
        (4 * math.pi * math.factorial(l + m)))

def SH(l, m, theta, phi):
    if m == 0:
        return SH_renormalization(l, m) * associated_legendre_polynomial(l, m, tf.cos(theta))
    elif m > 0:
        return math.sqrt(2.0) * SH_renormalization(l, m) * \
            tf.cos(m * phi) * associated_legendre_polynomial(l, m, tf.cos(theta))
    else:
        return math.sqrt(2.0) * SH_renormalization(l, -m) * \
            tf.sin(-m * phi) * associated_legendre_polynomial(l, -m, tf.cos(theta))

def SH_reconstruct(coeffs, res):
    uv = np.mgrid[0:res[1], 0:res[0]].astype(np.float32)
    theta = tf.convert_to_tensor((math.pi / res[1]) * (uv[1, :, :] + 0.5))
    phi = tf.convert_to_tensor((2 * math.pi / res[0]) * (uv[0, :, :] + 0.5))
    
    result = tf.constant(np.zeros([res[1], res[0], coeffs.shape[0]]), dtype=tf.float32)
    num_order = int(math.sqrt(coeffs.shape[1]))
    i = 0
    for l in range(num_order):
        for m in range(-l, l + 1):
            sh_factor = SH(l, m, theta, phi)
            result = result + sh_factor.view(sh_factor.shape[0], sh_factor.shape[1], 1) * coeffs[:, i]
            i += 1
    result = tf.math.maximum(result,
        tf.constant(np.zeros([res[1], res[0], coeffs.shape[0]]), dtype=tf.float32)
        )
    return result
#######################################################################################

def generate_sphere(theta_steps, phi_steps):
    """
    Use Numpy array for loop assignment as Tensorflow Tensors are not able to do that.
    """
    d_theta = math.pi / (theta_steps - 1)
    d_phi = (2 * math.pi) / (phi_steps - 1)

    vertices = np.zeros([theta_steps * phi_steps, 3])
    uvs = np.zeros([theta_steps * phi_steps, 2])

    vertices_index = 0
    for theta_index in range(theta_steps):
        sin_theta = math.sin(theta_index * d_theta)
        cos_theta = math.cos(theta_index * d_theta)
        for phi_index in range(phi_steps):
            sin_phi = math.sin(phi_index * d_phi)
            cos_phi = math.cos(phi_index * d_phi)
            vertices[vertices_index, :] = \
                np.array([sin_theta * cos_phi, cos_theta, sin_theta * sin_phi])
            uvs[vertices_index, 0] = theta_index * d_theta / math.pi
            uvs[vertices_index, 1] = phi_index * d_phi / (2 * math.pi)
            vertices_index += 1

    indices = []
    for theta_index in range(1, theta_steps):
        for phi_index in range(phi_steps - 1):
            id0 = phi_steps * theta_index + phi_index
            id1 = phi_steps * theta_index + phi_index + 1
            id2 = phi_steps * (theta_index - 1) + phi_index
            id3 = phi_steps * (theta_index - 1) + phi_index + 1

            if (theta_index < theta_steps - 1):
                indices.append([id0, id2, id1])
            if (theta_index > 1):
                indices.append([id1, id2, id3])

    indices = tf.convert_to_tensor(indices, dtype=tf.int32)
    vertices = tf.convert_to_tensor(vertices, dtype=tf.float32)
    uvs = tf.convert_to_tensor(uvs, dtype=tf.float32)


    normals = tf.identity(vertices)
    return (vertices, indices, uvs, normals)

############################################3
def read_tensor(filename, shape):
    """

    Args:
        filename(str)
        shape(np.array)
    """
    with open(filename) as f:
        tensor = np.array(f.readline().split(), dtype=np.float32)
        tensor = np.reshape(tensor, shape)

    return tensor
