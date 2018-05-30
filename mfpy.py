import os
import platform
import tempfile
import webbrowser
import shutil

import numpy as np
import pandas as pd
import flopy

os_name = platform.platform()
if os_name.startswith('Windows'):
    os.environ['PATH'] += ';' + os.path.abspath(
        os.path.join(os.path.dirname(__file__), 'bin')) +';'
elif os_name.startswith('Darwin'):
    os.environ['PATH'] += ':' + os.path.abspath(
        os.path.join(os.path.dirname(__file__), 'bin')) +':'

class Modflow(object):
    TIME_TO_INT = {
        'u': 0, 's': 1, 'm': 2, 'h': 3, 'd': 4, 'y': 5,
        }
    LEN_TO_INT = {
        'u': 0, 'f': 1, 'm': 2, 'c': 3,
        }

    def __init__(self, modflow_name='testing', model_name='mfpy',
        exe_name='mf2005', working_path=None):

        self.model_name = model_name
        self.modflow_name = modflow_name
        
        self.use_temp = None
        if working_path:
            self.use_temp = False
            self.working_path = working_path
        else:
            self.use_temp = True
            self.working_path = tempfile.mkdtemp()

        self.modflow = flopy.modflow.Modflow(
            model_name, exe_name = exe_name,
            model_ws=os.path.join(self.working_path, self.modflow_name))

    def cleanTemporalDirectory(self):
        if self.use_temp:
            shutil.rmtree(self.working_path)

    def changeDirectory(self, working_path, modflow_name):
        changed_dir = os.path.join(working_path, modflow_name)
        self.cleanTemporalDirectory()
        self.use_temp = False
        self.working_path = working_path
        self.modflow_name = modflow_name
        #auto create folder if not exists
        self.modflow.change_model_ws(changed_dir)

    def load(self, working_path, modflow_name='testing',
        model_name='mfpy'):
        working_path = os.path.abspath(working_path)
        if os.path.isdir(working_path):
            pass
        elif os.path.isfile(working_path):
            d, m_ext = os.path.split(working_path)
            working_path = os.path.split(d)[0]
            modflow_name = os.path.split(d)[1]
            model_name = os.path.splitext(m_ext)[0]
        else:
            raise ValueError('Not a valid path: {p}'.format(p=working_path))

        ori_wd = os.getcwd()
        os.chdir(os.path.join(
            working_path, modflow_name))
        self.modflow = flopy.modflow.Modflow.load(
            model_name+'.nam',
            exe_name='mf2005',
            model_ws=os.path.join(working_path, modflow_name),
            check=False)
        if os.path.exists('CHD.chk'):
            os.remove('CHD.chk')
        for p in self.modflow.get_package_list():
            setattr(self, p.lower(), self.modflow.get_package(p))
        hds_path = os.path.join(working_path, modflow_name, model_name+'.hds')
        if os.path.exists(hds_path):
            self.hds = flopy.utils.binaryfile.HeadFile(hds_path)
        self.cleanTemporalDirectory()
        self.use_temp = False
        self.working_path = working_path
        self.modflow_name = modflow_name
        self.model_name = model_name
        os.chdir(ori_wd)

    def setBas(self, ib, sh):
        self.bas6 = flopy.modflow.ModflowBas(
            self.modflow, ibound = ib, strt = sh)

    def setChd(self, spd):
        self.chd =\
            flopy.modflow.ModflowChd(
                self.modflow, stress_period_data = spd)

    def setDis(self, tp, bt, dr, dc, np_, pl, ns, iu, lu, st):
        if bt.ndim == 2: # skip layer, 1
            if tp.shape != bt.shape:
                raise ValueError(
                    "top and bottom should be the same shape "\
                    "when layer is ignored."
                    )
            bt = np.array([bt])
        nl, nr, nc = bt.shape
        st = [st] * np_ if isinstance(st, bool) else st
        iu = iu if isinstance(iu, int) else Modflow.TIME_TO_INT[iu[0].lower()]
        lu = lu if isinstance(lu, int) else Modflow.TIME_TO_INT[lu[0].lower()]

        self.dis = flopy.modflow.ModflowDis(
            self.modflow, nlay = nl, nrow = nr, ncol = nc, delr = dr, delc = dc, 
            top = tp, botm = bt, nper = np_, perlen = pl, nstp = ns,
            itmuni = iu, lenuni = lu, steady = st)

    def setLpf(self, **kwargs):
        self.lpf = flopy.modflow.ModflowLpf(
            self.modflow, **kwargs)

    def setModflowName(self, name):
        self.changeDirectory(self.working_path, name)


    def setOc(self, **kwargs):
        self.oc = flopy.modflow.ModflowOc(self.modflow, **kwargs)

    def setPcg(self):
        self.pcg = flopy.modflow.ModflowPcg(self.modflow)

    def setWel(self, spd):
        self.wel =\
            flopy.modflow.ModflowWel(
                self.modflow, stress_period_data = spd)

    def showDir(self):
        webbrowser.open(os.path.join(self.working_path, self.modflow_name))

    def run(self, write_input=True, silent=False):
        ori_p = os.getcwd()
        output_dir = os.path.join(self.working_path, self.modflow_name)
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)
        os.chdir(output_dir)
        if write_input:
            self.modflow.write_input()
        self.modflow.run_model(silent)
        for p in self.modflow.get_package_list():
            setattr(self, p.lower(), self.modflow.get_package(p))
        self.hds = flopy.utils.binaryfile.HeadFile(
            os.path.join(output_dir, self.model_name+'.hds'))
        os.chdir(ori_p)
