import torch
import matplotlib.pyplot as plt
from data import get_loaders, get_input_and_range, get_train_val_data
from create_argparser import get_parser_args
from pytorch_lightning.loggers import TensorBoardLogger
import pytorch_lightning as pl
from models.model import GenModule
import os
# from sheets import log_results
from cp import get_cp, get_cp_lists
from plotter import plot_prob, plot_path, plot_violin
from models.callbacks import get_callbacks
from baselines.lei import lei
from baselines.ridge import conf_pred
import random
import numpy as np
from cqr_helpers.run_cqr import run_cqr

torch.autograd.set_detect_anomaly(True)
def get_model(args):
    input_size, range_vals = get_input_and_range(args)

    model = GenModule(args, input_size, range_vals)

    total_path = "model_paths/{}.pth".format(args.model_path)
    if os.path.exists(total_path):
        model.load_state_dict(torch.load(total_path))
    else:
        train_loader, val_loader = get_loaders(args)
        logger = TensorBoardLogger("tb_logs", name=args.model_path)
        callbacks = get_callbacks(args)
        trainer = pl.Trainer(max_epochs=args.max_epochs, gpus=args.devices, logger=logger, callbacks=callbacks)
        trainer.fit(model, train_loader, val_loader)
        torch.save(model.state_dict(), total_path)
    model.eval()
    return model

def seed_everything(seed):
    random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

def main(args):
    X_train, y_train, X_val, y_val = get_train_val_data(args)

    input_size, range_vals = get_input_and_range(args)
    if args.cqr:
        mean_coverage, std_coverage, mean_length, std_length = run_cqr(args)
        log_results((args.dataset_name, args.model_path, mean_coverage, std_coverage, mean_length, std_length))
    if args.lei:
        mean_coverage, std_coverage, mean_length, std_length = lei(args)
        log_results((args.dataset_name, args.model_path, mean_coverage, std_coverage, mean_length, std_length))
    elif args.ridge:  
        mean_coverage, std_coverage, mean_length, std_length = conf_pred(args, lambda_=.1)
        log_results((args.dataset_name, args.model_path, mean_coverage, std_coverage, mean_length, std_length))
    elif args.plot_dcp:
        model = get_model(args) 
        mean_coverage, std_coverage, mean_length, std_length = get_cp(args, range_vals, X_val, y_val, model)
        plot_path(args, range_vals, X_val, y_val, model)
        plot_prob(args, range_vals, X_val, y_val, model)
    else:  
        model = get_model(args) 
        coverages, lengths = get_cp_lists(args, range_vals, X_val, y_val, model)
        mean_coverage, std_coverage, mean_length, std_length = get_cp(args, range_vals,  X_val, y_val, model)
        plot_prob(args, range_vals, X_val, y_val, model)
        log_results((args.dataset_name, args.model_path, mean_coverage, std_coverage, mean_length, std_length))
        plot_violin(args, coverages, lengths)
        
    return mean_coverage, std_coverage, mean_length, std_length

if __name__ == '__main__':
    torch.set_float32_matmul_precision('medium')
    for random_state_train_test_id in range(1):
        args = get_parser_args()
        setattr(args, "seed", random_state_train_test_id)
        seed_everything(random_state_train_test_id)
        main(args)
    