#!/usr/bin/env python3

from matplotlib.pyplot import axis
from collections import defaultdict

import matplotlib.pyplot as plt
import os
import glob 
import re
import argparse

def plot_filtered(ax: axis,  x: list, y: list, x_filter: str, marker: str, label: str, color=None):
   this_ts = list()
   this_all_rows = list()
   for ts, r in zip(x, y):
      if r.startswith(x_filter):
         this_ts.append(ts)
         this_all_rows.append(r)
   return ax.plot(this_ts, this_all_rows, marker, label=label, color=color) 

def plot_rows(fname: str, commands: list[str]):
   exp_root_dir = os.path.dirname(fname.replace("/data/decoded", ""))
   plot_output_dir = os.path.join(exp_root_dir, 'data', 'plots')
   print("[+] Experiment root directory: ", exp_root_dir)
   print("[+] Plot output directory: ", plot_output_dir)

   # if a folder was given, we need to find all decoded traces (csv files)
   num_subplots = 1
   files = [fname]
   if os.path.isdir(fname):
      files = glob.glob(f"{fname}/**/*.csv")
      num_subplots = len(files)

   print("[+] Files to be plotted:", ','.join([os.path.basename(f) for f in files]))
   print("[+] Number of subplots:", num_subplots)

   # if a single csv file was given as input, then num_subplots==1
   if num_subplots == 1:
      fig, axs = plt.subplots(num_subplots, figsize=(192, 16))
      # make sure 'axs' is in both cases a list of axes
      axs = [axs]
   else:
      fig, axs = plt.subplots(num_subplots, figsize=(512, 8*num_subplots))

   # go through all the files and plot them individually
   for fn, ax in zip(files, axs):
      plt.set_cmap('tab10')
      plt.tick_params(labelright=True)
      plt.grid(color='0.9', linestyle='solid', linewidth=0.1, which='major', axis='y')
      plt.title(f"file: {fn.replace('/mnt/scope-data/','')}", loc='left')

      ax.set_ylabel("bg,bk,row [dec]")
      ax.set_xlabel("time [sec]")
      ax.set_autoscaley_on(True)
      ax.autoscale()
      ax.margins(x=0.005)
      ax.margins(y=0.005)

      with open(fn) as f:
         # ACT
         all_act_data = list()
         all_act_ts = list()
         # REFab
         all_refab_ts = list()
         # REFsb
         all_refsb_ts = defaultdict(list)
         # WR(a)
         all_write_data = list()
         all_write_ts = list()
         # RD(a)
         all_read_data = list()
         all_read_ts = list()

         # this is to know to which row RD/WR are going to
         last_activated_row_per_bgbk = defaultdict(list)

         print("[+] Processing file:", fn)

         y_axis_labels = list()
         # skip header, start by line 2
         for l in f.readlines()[1:]:
            ts, cmd, bg, bk, row, col = l.replace("\n","").split(",")
            bg = int(bg,2) if bg != '' else ''
            bk = int(bk,2) if bk != '' else ''
            row = int(row,2) if row != '' else ''
            col = int(col,2) if col != '' else ''
            
            # parse the commands and extract command-specific data
            key = None
            if cmd == "act" and 'act' in commands:
               all_act_ts.append(float(ts))
               key = f"{bg},{bk},{row}"
               all_act_data.append(key)
               last_activated_row_per_bgbk[f"{bg},{bk}"].append(row)
            elif cmd in ["rd", "rda"] and 'rd' in commands:
               if len(last_activated_row_per_bgbk[f"{bg},{bk}"]) < 1:
                   continue
               all_read_ts.append(float(ts))
               last_row = last_activated_row_per_bgbk[f"{bg},{bk}"][-1]
               key = f"{bg},{bk},{last_row},{col}"
               all_read_data.append(key)
            elif cmd in ["wr", "wra"] and 'wr' in commands:
               if len(last_activated_row_per_bgbk[f"{bg},{bk}"]) < 1:
                   continue
               all_write_ts.append(float(ts))
               last_row = last_activated_row_per_bgbk[f"{bg},{bk}"][-1]
               key = f"{bg},{bk},{last_row},{col}"
               all_write_data.append(key)
            elif cmd == "ref_sb" and 'ref_sb' in commands:
               all_refsb_ts[bk].append(float(ts))
            elif cmd == "ref_ab" and 'ref_ab' in commands:
               all_refab_ts.append(float(ts))
            else:
               continue

            # collect y-axis labels (bg,bk) or (bg,bk,row)
            if key is not None:
               y_axis_labels.append(key)
         
         # plot everything, use one color per <bg,bk> combination but different
         # markers for ACT, RD, WR
         bg_bk = list(dict.fromkeys([','.join(v.split(',')[0:2]) for v in y_axis_labels]))
         map_bgbk2color = dict()
         for conf in bg_bk:
            p = plot_filtered(ax, all_act_ts, all_act_data, conf, 'o', f'ACT({conf})')
            map_bgbk2color[conf] = p[-1].get_color()
            _ = plot_filtered(ax, all_read_ts, all_read_data, conf, 'x', f'RD*({conf})', color=map_bgbk2color[conf]) 
            _ = plot_filtered(ax, all_write_ts, all_write_data, conf, '^', f'WR*({conf})', color=map_bgbk2color[conf])

         # this must be called after having called the plot function to not cause a warning msg
         plt.legend(loc='upper left')

         # add vertical lines for REFsb commands (blue) with text label to indicate the targeted bk
         for bk, refsb_list in all_refsb_ts.items():
            linestyle = '--'
            alpha = 0.4
            # if int(bk) == TARGET_BK:
            #    linestyle = 'solid'
            #    alpha = 1.0
            for x in refsb_list:
               ax.axvline(x=x, color='b', alpha=alpha, linestyle=linestyle)
               t = ax.text(x,0,
                     f"bk={bk}", rotation=90,
                     verticalalignment='center', horizontalalignment='center',
                     backgroundcolor='w', fontweight='light', fontsize='x-small')
               t.set_bbox(dict(facecolor='white', alpha=0.5, linewidth=0))

         # add vertical lines for REFab commands (green)
         for x in all_refab_ts:
            ax.axvline(x=x, color='g', linewidth=2.0)

   # write the plot to disk in the './data/plotting/' directory
   os.makedirs(plot_output_dir, exist_ok=True)
   if num_subplots == 1:
      destination = os.path.join(plot_output_dir, os.path.basename(fname).replace('.csv','.pdf'))
   else:
      fig.tight_layout()
      destination = os.path.join(plot_output_dir, f"plot_all.pdf")

   print("[+] Writing file:", destination)
   fig.savefig(destination, dpi=300, bbox_inches='tight')

def main():
   parser = argparse.ArgumentParser(
      prog='plot_rows.py -- row-based plotter',
      description='Plots acquired scope data over time (x-axis) per row (y-axis).')
   parser.add_argument('input_file_or_directory', 
      help="a file or directory with decoded scope data (i.e., must end with '/data/decoded')")
   parser.add_argument('--commands', 
      action='append', 
      default=['act', 'ref_ab', 'ref_sb'], 
      help="commands to be considered in the plot")

   args = parser.parse_args()
   fname = args.input_file_or_directory

   print("[+] Processing file/folder:", fname)
   plot_rows(fname, args.commands)

if __name__ == "__main__":
   main()
