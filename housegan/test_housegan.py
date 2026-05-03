import argparse
import os
import numpy as np
import math
import sys
import random
import torch
import torchvision.transforms as transforms
from torchvision.utils import save_image
from floorplan_dataset_maps import FloorplanGraphDataset, floorplan_collate_fn
from torch.utils.data import DataLoader
from torch.autograd import Variable
import torch.nn as nn
from PIL import Image, ImageDraw
import webcolors
import cv2
import matplotlib.pyplot as plt
import networkx as nx

# Mock reconstructFloorplan if it fails
try:
    from reconstruct import reconstructFloorplan
except ImportError:
    def reconstructFloorplan(*args, **kwargs):
        return None

from utils import bb_to_img, bb_to_vec, bb_to_seg, mask_to_bb, remove_junctions, ID_COLOR, bb_to_im_fid
from models import Generator

# Override draw_graph to avoid pygraphviz
def draw_graph_custom(g_true):
    G_true = nx.Graph()
    colors_H = []
    for k, label in enumerate(g_true[0]):
        _type = label+1 
        if _type >= 0:
            G_true.add_nodes_from([(k, {'label':_type})])
            # Handle potential index error in ID_COLOR
            color = ID_COLOR[_type] if _type < len(ID_COLOR) else 'gray'
            colors_H.append(color)
    for k, m, l in g_true[1]:
        if m > 0:
            G_true.add_edges_from([(k, l)], color='b', weight=4)    
    
    plt.figure(figsize=(5,5))
    # Use spring_layout instead of graphviz_layout
    pos = nx.spring_layout(G_true)
    
    edges = G_true.edges()
    colors = ['black' for u,v in edges]
    weights = [4 for u,v in edges]

    nx.draw(G_true, pos, node_size=1000, node_color=colors_H, font_size=0, font_weight='bold', edgelist=edges, edge_color=colors, width=weights)
    plt.tight_layout()
    os.makedirs("./dump/", exist_ok=True)
    plt.savefig('./dump/_true_graph.jpg', format="jpg")
    plt.close()
    
    rgb_im = Image.open('./dump/_true_graph.jpg')
    # Reuse pad_im logic
    new_size = 256
    padded_im = Image.new('RGB', (new_size, new_size), 'white')
    rgb_im.thumbnail((new_size, new_size))
    padded_im.paste(rgb_im, ((new_size-rgb_im.size[0])//2, (new_size-rgb_im.size[1])//2))
    rgb_arr = padded_im.convert('RGBA')
    return rgb_arr

def draw_masks_custom(masks, real_nodes):
    bg_img = Image.new("RGBA", (256, 256), (255, 255, 255, 0)) 
    for m, nd in zip(masks, real_nodes):
        reg = Image.new('RGBA', (32, 32), (0,0,0,0))
        dr_reg = ImageDraw.Draw(reg)
        m_np = m.detach().cpu().numpy()
        m_np[m_np>0] = 255
        m_np[m_np<0] = 0
        m_im = Image.fromarray(m_np.astype('uint8'))
        color = ID_COLOR[nd+1]
        r, g, b = webcolors.name_to_rgb(color)
        dr_reg.bitmap((0, 0), m_im.convert('L'), fill=(r, g, b, 32))
        reg = reg.resize((256, 256), Image.NEAREST)
        bg_img.paste(Image.alpha_composite(bg_img, reg))

    for m, nd in zip(masks, real_nodes):
        cnt = Image.new('RGBA', (256, 256), (0,0,0,0))
        dr_cnt = ImageDraw.Draw(cnt)
        m_np = m.detach().cpu().numpy()
        m_np[m_np>0] = 255
        m_np[m_np<=0] = 0
        m_np = cv2.resize(m_np, (256, 256), interpolation = cv2.INTER_AREA) 
        ret,thresh = cv2.threshold(m_np.astype('uint8'),127,255,0)
        contours, _ = cv2.findContours(thresh,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
        
        mask = np.zeros((256,256,3)).astype('uint8')
        color = ID_COLOR[nd+1]
        r, g, b = webcolors.name_to_rgb(color)
        cv2.drawContours(mask, contours, -1, (255, 255, 255), 2)
        mask_im = Image.fromarray(mask)
        dr_cnt.bitmap((0, 0), mask_im.convert('L'), fill=(r, g, b, 255))
        bg_img.paste(Image.alpha_composite(bg_img, cnt))
    return bg_img

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=str, default='./checkpoints/exp_demo_D_500000.pth')
    parser.add_argument("--data_path", type=str, default='./')
    parser.add_argument("--num_variations", type=int, default=2)
    parser.add_argument("--output_folder", type=str, default='./output/')
    opt = parser.parse_args()

    os.makedirs(opt.output_folder, exist_ok=True)
    os.makedirs("./dump/", exist_ok=True)

    generator = Generator()
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    generator.load_state_dict(torch.load(opt.checkpoint, map_location=device))
    generator.to(device)
    generator.eval()

    print("Model loaded.")

    fp_dataset_test = FloorplanGraphDataset(opt.data_path, transforms.Normalize(mean=[0.5], std=[0.5]), target_set='D', split='eval')
    fp_loader = DataLoader(fp_dataset_test, batch_size=1, shuffle=False, collate_fn=floorplan_collate_fn)

    print(f"Dataset loaded. Total samples: {len(fp_dataset_test)}")

    Tensor = torch.cuda.FloatTensor if torch.cuda.is_available() else torch.FloatTensor

    final_images = []
    for i, batch in enumerate(fp_loader):
        if i >= 5: # Just test 5 samples
            break
        
        print(f"Processing sample {i}...")
        mks, nds, eds, nd_to_sample, ed_to_sample = batch
        real_mks = Variable(mks.type(Tensor))
        given_nds = Variable(nds.type(Tensor))
        given_eds = eds
        
        real_nodes = np.where(given_nds.detach().cpu()==1)[-1]
        
        # Draw ground truth graph
        graph_arr = draw_graph_custom([real_nodes, eds.detach().cpu().numpy()])
        final_images.append(graph_arr)

        for k in range(opt.num_variations):
            z = Variable(Tensor(np.random.normal(0, 1, (real_mks.shape[0], 128))))
            with torch.no_grad():
                gen_mks = generator(z, given_nds, given_eds)
                # gen_mks shape: [N, 32, 32]
            
            # Draw generated layout (masks)
            fake_im_seg = draw_masks_custom(gen_mks, real_nodes)
            final_images.append(fake_im_seg)
            
            # Draw generated layout (bounding boxes)
            gen_bbs = np.array([np.array(mask_to_bb(mk)) for mk in gen_mks.detach().cpu()])
            gen_bbs = gen_bbs[np.newaxis, :, :]/32.0
            fake_im_bb = bb_to_im_fid(gen_bbs, real_nodes, im_size=256).convert('RGBA')
            final_images.append(fake_im_bb)

    # Save results
    if final_images:
        # Convert list of PIL images to a grid and save
        # For simplicity, just save them one by one or use torch save_image
        print(f"Saving {len(final_images)} images...")
        torch_images = []
        for im in final_images:
            arr = np.array(im).transpose((2, 0, 1)) # [4, 256, 256]
            torch_images.append(torch.tensor(arr[:3, :, :]) / 255.0) # Take RGB only
        
        grid = torch.stack(torch_images)
        save_image(grid, os.path.join(opt.output_folder, "test_results.png"), nrow=1 + 2*opt.num_variations)
        print("Results saved to output/test_results.png")

if __name__ == "__main__":
    main()
