import torch
import numpy as np
import os
import sys
from PIL import Image
from torch.autograd import Variable

# Add current directory to path to ensure relative imports work
sys.path.append(os.path.dirname(__file__))

from models import Generator
from utils import ROOM_CLASS, mask_to_bb, bb_to_im_fid, align_bb

_generator_instance = None
_current_device = None

def load_model(checkpoint_path, device=None):
    global _generator_instance, _current_device
    if device is None:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    if _generator_instance is None or _current_device != device:
        print(f"Loading HouseGAN model from {checkpoint_path} on {device}...")
        generator = Generator()
        # Use absolute path if relative
        if not os.path.isabs(checkpoint_path):
            checkpoint_path = os.path.join(os.path.dirname(__file__), checkpoint_path)
        
        generator.load_state_dict(torch.load(checkpoint_path, map_location=device))
        generator.to(device)
        generator.eval()
        _generator_instance = generator
        _current_device = device
    return _generator_instance

def one_hot_embedding(labels, num_classes=11):
    y = torch.eye(num_classes) 
    return y[labels]

def generate_plan_from_graph(room_names, edges_list, checkpoint_path=None, num_variations=3):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    if checkpoint_path is None:
        checkpoint_path = os.path.join(os.path.dirname(__file__), 'checkpoints', 'exp_demo_D_500000.pth')
    
    # Load or get cached generator
    generator = load_model(checkpoint_path, device)
    
    # Prepare nodes
    nodes_indices = []
    for name in room_names:
        # Normalize name and find index
        clean_name = name.lower().strip().replace(" ", "_")
        idx = ROOM_CLASS.get(clean_name, 5) # Default to 5 (missing/red)
        nodes_indices.append(idx)
    
    if not nodes_indices:
        return Image.new('RGB', (512, 512), 'white')

    nodes_tensor = one_hot_embedding(torch.LongTensor(nodes_indices))[:, 1:]
    num_nodes = len(room_names)
    triples = []
    
    pos_edges = set()
    for e in edges_list:
        if len(e) >= 2:
            u, v = sorted([e[0], e[1]])
            pos_edges.add((u, v))
        
    for i in range(num_nodes):
        for j in range(i + 1, num_nodes):
            if (i, j) in pos_edges:
                triples.append([i, 1, j])
            else:
                triples.append([i, -1, j])
                
    if not triples:
        # Single room case
        pass

    edges_tensor = torch.LongTensor(triples)
    nodes_batch = nodes_tensor.to(device)
    edges_batch = edges_tensor.to(device)
    
    latent_dim = 128
    all_imgs = []
    
    for _ in range(num_variations):
        z = Variable(torch.FloatTensor(np.random.normal(0, 1, (nodes_batch.shape[0], latent_dim))).to(device))
        with torch.no_grad():
            gen_mks = generator(z, nodes_batch, edges_batch)
            
        gen_bbs = np.array([np.array(mask_to_bb(mk)) for mk in gen_mks.detach().cpu()])
        gen_bbs = gen_bbs[np.newaxis, :, :]/32.0
        
        # Post-process: Align bounding boxes to snap edges together
        gen_bbs = align_bb(gen_bbs)
        
        real_nodes = np.array(nodes_indices) - 1
        plan_im = bb_to_im_fid(gen_bbs, real_nodes, im_size=512)
        all_imgs.append(plan_im)
    
    # Combine images into a horizontal grid
    widths, heights = zip(*(i.size for i in all_imgs))
    total_width = sum(widths)
    max_height = max(heights)
    
    new_im = Image.new('RGB', (total_width, max_height))
    x_offset = 0
    for im in all_imgs:
        new_im.paste(im, (x_offset, 0))
        x_offset += im.size[0]
        
    return new_im

if __name__ == "__main__":
    # Test
    rooms = ["living_room", "kitchen", "bedroom", "bathroom"]
    edges = [[0, 1], [0, 2], [2, 3]]
    img = generate_plan_from_graph(rooms, edges)
    img.save("test_custom.png")
    print("Saved test_custom.png")
