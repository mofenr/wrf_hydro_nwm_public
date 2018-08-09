from boltons import iterutils
import os
import pathlib
import subprocess
from wrfhydropy import JSONNamelist

# Example: python get_config_file_meta_data
#
# 1) Run script file in-place, in this directory, as above.
# 2) Typically, this will be run on cheyenne since that's where CONUS domain
#    files will live.
# 3) Configure the list of domains paths and configs below.
# 4) The dirs in this directory must be removed to be refreshed.
# 5) This script skips non-existent files and ignores timeslices.

domain_paths = [
    "/glade/work/jamesmcc/domains/public/croton_NY",
    "/glade/work/jamesmcc/domains/private/CONUS"
]

configs = [
    'nwm_ana',
    'nwm_long_range'
]

# -----------------------------------
domain_paths = [pathlib.PosixPath(pp) for pp in domain_paths]
this_path = pathlib.PosixPath(os.getcwd())
code_path = this_path.parent.parent / 'trunk/NDHMS/'

def get_nlst_file_meta(
    namelist: dict,
    dom_dir: str
):

    def visit_missing_file(path, key, value):

        # Only treat strings
        if type(value) is not str:
            return False

        # Convert to pathlib object, kee        
        the_file_rel = pathlib.PosixPath(value)
        the_file_abs = dom_dir / the_file_rel

        # Do not treat dirs.
        if the_file_abs.is_dir():
            return False

        print('            ' + str(the_file_abs))

        if the_file_abs.exists() is False:
            raise ValueError("The file does not exist: " + str(the_file_abs))
        
        # The sub process command is executed in the root of the meta path,
        # use the relative data path/
        meta_path_rel = the_file_rel
        the_cmd = 'meta_path=' + str(meta_path_rel)
        the_cmd += ' && data_path=' + str(the_file_abs)
        the_cmd += ' && mkdir -p $(dirname $meta_path)'
        the_cmd += ' && echo "md5sum: $(md5sum $data_path)" > $meta_path'
        the_cmd += ' && echo "ncdump -h: $(ncdump -h $data_path)" >> $meta_path'
        proc = subprocess.run(
            the_cmd,
            cwd=config_dir,
            shell=True,
            executable='/bin/bash'
        )
        
        return True

    _ = iterutils.remap(namelist, visit=visit_missing_file)

    
for dd in domain_paths:

    print('')
    print('Domain: ' + str(dd))

    domain_tag = dd.name
    
    for cc in configs:

        print('')
        print('    Config: ' + str(cc))
        
        # Make a meta data output dir for each configuration.
        config_dir = (this_path / domain_tag) / cc
        config_dir.mkdir(parents=True, exist_ok=False)
        
        # Create the namelists
        domain_nlsts = ['hydro_namelists.json', 'hrldas_namelists.json']
        code_nlsts = ['hydro_namelist_patches.json', 'hrldas_namelist_patches.json']
        file_names = ['hydro.namelist', 'namelist.hrldas']
        
        for code, dom, ff in zip(domain_nlsts, code_nlsts, file_names):

            print('        Namelist: ' + str(ff))
            repo_namelists = JSONNamelist(code_path / code)
            domain_namelists = JSONNamelist(dd / dom)
            
            repo_config = repo_namelists.get_config(cc)
            domain_config = domain_namelists.get_config(cc)

            patched_namelist = repo_config.patch(domain_config)

            # Write them out for completeness.
            patched_namelist.write(str(config_dir / ff))         
            
            # This function does the work.
            get_nlst_file_meta(patched_namelist, dd)

