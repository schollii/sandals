class TempChDir:
    """
    Context manager to step into a directory temporarily. Use in a `with` block: 
    
      with TempChDir(path):
          ...do stuff...
        
    This automatically changes cwd if necessary, upon entry of the block, and 
    changes it back on exit. Note that if `path` is ".", this is
    a null operation, which can be handy in some situations. 
    """
    info = None

    def __init__(self, path: Path):
        self.old_dir = None
        self.new_dir = Path(path).expanduser().absolute()

        cwd = Path.cwd().absolute()
        if cwd != self.new_dir:
            self.old_dir = cwd

    def __enter__(self):
        if self.old_dir:
            if self.info: 
                self.info(f'Changing CWD to {self.new_dir} (temporarily)')
            os.chdir(self.new_dir)

    def __exit__(self, *args):
        if self.old_dir:
            if self.info: 
                self.info(f'Changing CWD back to {self.old_dir}')
            os.chdir(self.old_dir)
