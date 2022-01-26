import argparse, os
import pandas as pd
from ._scAR import model
from . import _data_loader as dataloader

def main():
    
    ##########################################################################################
    ## argument parser
    ##########################################################################################

    parser = argparse.ArgumentParser(description='single cell Ambient Remover (scAR): remove ambient signals for scRNAseq data')
    parser.add_argument('count_matrix', type=str, nargs='+', help='the file of observed count matrix, 2D array (cells x genes)')
    parser.add_argument('-e','--empty_profile', type=str, default=None, help='the file of empty profile obtained from empty droplets, 1D array')
    parser.add_argument('-t', '--technology', type=str, default='scRNAseq', help='scRNAseq technology, e.g. scRNAseq, CROPseq, CITEseq, ... etc.')
    parser.add_argument('-o', '--output', type=str, default=None, help='output directory')
    parser.add_argument('-tb', '--TensorBoard', type=str, default=False, help='Tensorboard directory')
    
    parser.add_argument('-hl1', '--hidden_layer1', type=int, default=None, help='number of neurons in the first layer')
    parser.add_argument('-hl2', '--hidden_layer2', type=int, default=None, help='number of neurons in the second layer')
    parser.add_argument('-ls', '--latent_space', type=int, default=None, help='dimension of latent space')
    parser.add_argument('-epo', '--epochs', type=int, default=800, help='training epochs')
    parser.add_argument('-s', '--save_model', type=int, default=False, help='whether save the trained model')
    parser.add_argument('-plot', '--plot_every_epoch', type=int, default=50, help='plot every epochs')
    parser.add_argument('-batchsize', '--batchsize', type=int, default=64, help='batch size')

    args = parser.parse_args()

    count_matrix_path = args.count_matrix[0]
    empty_profile_path = args.empty_profile
    scRNAseq_tech = args.technology
    output_dir = os.getcwd() if not args.output else args.output  # if None, output to current directory
    TensorBoard = args.TensorBoard
    NN_layer1 = args.hidden_layer1
    NN_layer2 = args.hidden_layer2
    latent_space = args.latent_space
    epochs = args.epochs
    save_model = args.save_model
    plot_every_epoch = args.plot_every_epoch
    batch_size = args.batchsize
    
    print('===========================================')
    print('scRNAseq_tech: ', scRNAseq_tech)
    print('output_dir: ', output_dir)
    print('count_matrix_path: ', count_matrix_path)
    print('empty_profile_path: ', empty_profile_path)
    print('TensorBoard path: ', TensorBoard)
    
    # Read data
    print('===========================================\n  Reading data...')
    print('-------------------------------------------')
    count_matrix = pd.read_pickle(count_matrix_path)
    count_matrix = count_matrix.fillna(0) # replace missing values with zeros
    print('  ... count_matrix:')
    count_matrix.info(max_cols=10)
    
    if args.empty_profile:
        empty_profile = pd.read_pickle(empty_profile_path)
        print(' ... calculate empty profile using empty droplets')
        assert (empty_profile.index == count_matrix.columns).all()        
    else:
        empty_profile = count_matrix.sum(axis=0)/count_matrix.sum().sum()
        empty_profile = empty_profile.to_frame()
        print(' ... calculate empty profile using cell-containing droplets')
        
    print('-------------------------------------------')
    print(' ... empty_profile:')
    empty_profile = empty_profile.fillna(0) # replace missing values with zeros
    empty_profile.info(max_cols=10)
    
    print('===========================================\n  Loading data to dataloader...')
    train_set, val_set, total_set = dataloader.get_dataset(count_matrix.values, empty_profile.values, split=0.002, batch_size=batch_size)

    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    # Run model
    scARObj = model(train_set,
                    val_set,
                    total_set,
                    num_input_feature=count_matrix.shape[1],
                    NN_layer1=NN_layer1,
                    NN_layer2=NN_layer2,
                    latent_space=latent_space,
                    scRNAseq_tech=scRNAseq_tech)
    
    scARObj.train(epochs=epochs,
                  plot_every_epoch=plot_every_epoch,
                  batch_size=batch_size,
                  TensorBoard=TensorBoard,
                  save_model=save_model)
    
    print('===========================================\n  Saving results...')
    output_path01, output_path02, output_path03, output_path04 = os.path.join(output_dir, f'denoised_counts.pickle'), os.path.join(output_dir, f'BayesFactor.pickle'), os.path.join(output_dir, f'native_frequency.pickle'), os.path.join(output_dir, f'noise_ratio.pickle')
  
    # save results
    pd.DataFrame(scARObj.native_counts, index=count_matrix.index, columns=count_matrix.columns).to_pickle(output_path01)
    pd.DataFrame(scARObj.bayesfactor, index=count_matrix.index, columns=count_matrix.columns).to_pickle(output_path02)
    pd.DataFrame(scARObj.native_frequencies, index=count_matrix.index, columns=count_matrix.columns).to_pickle(output_path03)
    pd.DataFrame(scARObj.noise_ratio, index=count_matrix.index, columns=['noise_ratio']).to_pickle(output_path04)
    
    print(f'...denoised counts saved in: {output_path01}')
    print(f'...BayesFactor matrix saved in: {output_path02}')
    print(f'...expected native frequencies saved in: {output_path03}')
    print(f'...expected noise ratio saved in: {output_path04}')
    
    print(f'===========================================\n  Done!!!')

if __name__ == "__main__":
    main()