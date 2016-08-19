import os
import sys
import numpy
import pickle
import zipfile
import urllib2
import subprocess

import matplotlib
matplotlib.use('Agg') #don't use X backend so headless servers don't die

from matplotlib import pyplot


def pickleload(filename):
    """
    Does what it says.  Loads a pickle (and returns it)
    """
    with open(filename, 'r') as f:
        results_dict = pickle.load(f)

    return results_dict


def compile_dict_results(files):
    """
    Compiles a dict of lists of like results given a list of
    dictionaries containing results

    Inputs
    ------
        files: list of strings
            strings of filenames of input dicts

    Returns
    -------
        compiled_results: dict of lists
            dictionary where keyname is same as input dicts but corresponding
            value is a list containing all results that have the same key
    """
    compiled_results = {}
    for filename in files:
        results_dict = pickleload(filename)
        for k, v in results_dict.items():
            if k in compiled_results.keys():
                compiled_results[k].append(v)
            else:
                compiled_results[k] = [v]

    return compiled_results


def richardson_extrapolation(compiled_results):
    """
    Performs an estimate of the exact solution using
    Richardson extrapolation, given by

    f_ex = (f_1 * f_3 - f_2^2) / (f_3 - 2*f_2+f_1)

    where f_1 is a result from the finest grid and f_3 is from the coarsest.
    The grids f_1, f_2, f_3 should have the same refinement ratio (e.g. 2 -> 4 -> 8)
    """

    try:
        esolv = compiled_results['E_solv_kJ']
    except KeyError:
        print('No results found for solvation energy.  \n'
              'Something has gone wrong.')
        sys.exit()
    f1 = esolv[5] # assuming 6 runs: 1, 2, 4, 8, 12, 16
    f2 = esolv[3]
    f3 = esolv[2]

    return (f1 * f3 - f2**2) / (f3 - 2 * f2 + f1)



def generate_plot(compiled_results, filetype='pdf'):
    """
    Generates a plot with some hard-coded info based on APBS runs
    """
    res = compiled_results
    N_fem = numpy.array([97*65*97, 129*97*129, 161*129*161, 257*161*257, 385*257*385, 449*385*449,513*449*513])
    Vfem = 50.*40.*50.
    Lfem = (Vfem/N_fem)**(1/3.)
    Lfem_aux = numpy.array([[0.521,0.625,0.521],[0.391,0.417,0.391],
                            [0.312,0.312,0.312],[0.195,0.250,0.195],
                            [0.130,0.156,0.130],[0.112,0.104,0.112],
                            [0.098,0.089,0.098]])
    timeAPB = numpy.array([4.3,8.6,17.7,54,161,352,768])
    EsolvAPB = numpy.array([-2237,-2172.9,-2142,-2121.5,-2102.6,-2093.7,-2090.7])
    apb_ext = -2070.47

    pyg_ext = richardson_extrapolation(res)

    font = {'family':'serif', 'size':7}
    pyplot.figure(figsize=(3, 2), dpi=80)
    pyplot.rc('font', **font)

    #calc plot extremas for plotting
    xmax = N_fem[-1]*5
    xmin = res['total_elements'][0] / 1.5

    pyplot.semilogx(res['total_elements'], res['E_solv_kJ'],
                    c='k', marker='o', mfc='w', ms=3, ls='-', lw=0.5, label='PyGBe')
    pyplot.semilogx(N_fem, EsolvAPB,
                    c='k', marker='^', mfc='w', ms=3, ls='-', lw=0.5, label='APBS')
    pyplot.semilogx([xmin,xmax],pyg_ext*numpy.ones(2), c='k', marker='', mfc='w', ms=1, ls='dotted',lw=0.2)
    pyplot.semilogx([xmin,xmax],apb_ext*numpy.ones(2), c='k', marker='', mfc='w', ms=1, ls='dotted',lw=0.2)

    pyplot.ylabel('$\Delta G_{solv}$ [kJ/mol]', fontsize=10)
    pyplot.xlabel('N',fontsize=10)
    pyplot.text(5e5, pyg_ext - 25,'PyGBe extrap.',fontsize=6,rotation=0)
    pyplot.text(1e7, -2067,'APBS extrap.',fontsize=6,rotation=0)
    pyplot.subplots_adjust(left=0.22, bottom=0.21, right=0.96, top=0.95)
    pyplot.axis([xmin,xmax,-2450,-2040])
    pyplot.legend(loc='lower right')
    fname = 'Esolv_lys.{}'.format(filetype)
    print('Writing figure to "{}"'.format(fname))
    pyplot.savefig(fname)


    pygbe_err = numpy.abs(numpy.array(res['E_solv_kJ']) - pyg_ext) / numpy.abs(pyg_ext)
    apb_err = numpy.abs(EsolvAPB - apb_ext) / numpy.abs(apb_ext)

    pyplot.figure(figsize=(3, 2), dpi=80)
    pyplot.loglog(pygbe_err, res['total_time'],
                  c='k', marker='o', mfc='w', ms=5,
                  ls='-',lw=0.5, label='PyGBe')
    pyplot.loglog(apb_err, timeAPB,
                  c='k', marker='^', mfc='w', ms=5,
                  ls='-',lw=0.5, label='APBS')
    pyplot.subplots_adjust(left=0.19, bottom=0.21, right=0.96, top=0.95)
    pyplot.ylabel('Time to solution [s]',fontsize=10)
    pyplot.xlabel('Error',fontsize=10)
    pyplot.legend(loc='lower left')
    fname = 'time_lys.{}'.format(filetype)
    print('Writing figure to "{}"'.format(fname))
    pyplot.savefig(fname)

    pyplot.figure(figsize=(3,2), dpi=80)
    pyplot.loglog(res['total_elements'], res['total_time'],
                  c='k', marker='o', mfc='w', ms=5,
                  ls='-',lw=0.5)
    pyplot.xlabel('Number of elements', fontsize=10)
    pyplot.ylabel('Time to solution [s]', fontsize=10)
    pyplot.subplots_adjust(left=0.19, bottom=0.21, right=0.96, top=0.95)
    fname = 'time_v_N_lys.{}'.format(filetype)
    print('Writing figure to "{}"'.format(fname))
    pyplot.savefig(fname)


def check_mesh():
    """
    Check if there is a geometry folder already present in the current location.
    If not, download the mesh files from Zenodo.
    """
    if not os.path.isdir('geometry'):
        dl_check = input('The meshes for the performance check don\'t appear '
                         'to be loaded. Would you like to download them from '
                             'Zenodo? (~11MB) (y/n): ')
        if dl_check == 'y':
            mesh_file = 'https://zenodo.org/record/58308/files/lysozyme_meshes.zip'
            download_zip_with_progress_bar(mesh_file)
            unzip(mesh_file.split('/')[-1])

            print('Done!')


def download_zip_with_progress_bar(url):
    file_name = url.split('/')[-1]
    u = urllib2.urlopen(url)
    f = open(file_name, 'wb')
    meta = u.info()
    file_size = int(meta.getheaders("Content-Length")[0])
    print "Downloading: %s Bytes: %s" % (file_name, file_size)

    file_size_dl = 0
    block_sz = 8192
    while True:
        buffer = u.read(block_sz)
        if not buffer:
            break

        file_size_dl += len(buffer)
        f.write(buffer)
        status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
        status = status + chr(8)*(len(status)+1)
        print status,

    f.close()


def unzip(meshzip):
    with zipfile.ZipFile(meshzip, 'r') as myzip:
        myzip.extractall(path='.')

    print('Unzipping meshes ...')
    print('Removing zip file...')
    os.remove(meshzip)


def run_check():
    """
    Use subprocess to run through the 6 cases to generate results
    """
    try:
        os.mkdir('output')
    except OSError:
        pass
    if [a for a in os.listdir('output') if 'pickle' in a]:
        run_check_yn = input('\n\n\n'
                              'There are already results in your output directory.  '
                              'Do you want to re-run the tests?  If you select "no" '
                              'then the plotting routine will still run.  If you select '
                              '"yes", note that this script is not smart enough to '
                              'distinguish between "old" and "new" runs and will just '
                              'jam everything together into one figure (yes/no): ')

        if run_check_yn in ['No', 'no', 'n']:
            return
        elif run_check_yn in ['Yes', 'yes', 'y']:
            run_lysozome()
        else:
            print('Didn\'t understand your response, exiting')
            sys.exit()

    else:
        run_lysozome()

def run_lysozome():
    conf_files = ['lys.config', 'lys2.config', 'lys4.config',
                'lys8.config', 'lys12.config', 'lys16.config']
    for conf in conf_files:
        subprocess.call(['pygbe', '-c', conf, '-p', 'lys.param', '.'])


def main():
    run_yn = input('This will run 6 lysozyme cases in order to generate '
                       'results necessary to generate a few figures. It '
                       'takes around 10 minutes to run on a Tesla K40 '
                       'and also time to download meshes from Zenodo (~11MB).  '
                       'Type "y" or some variant of yes to accept this: ')

    if run_yn in ['Yes', 'yes', 'y', 'Y']:
        #check that meshes are present
        check_mesh()
        #run the lysozome problems
        run_check()
        files = [os.path.join('output', a)
                 for a in os.listdir('output') if 'pickle' in a]
        files.sort()
        compiled_results = compile_dict_results(files)
        generate_plot(compiled_results, filetype='pdf')
        return compiled_results

if __name__ == '__main__':
    main()
