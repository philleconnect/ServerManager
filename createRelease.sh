#!/bin/bash

mkdir servermanager
cp config.py servermanager/
cp dockerdelete.py servermanager/
cp servermanager.py servermanager/
cp update.py servermanager/
cp volumebackup.py servermanager/
cp -R modules servermanager/
tar cfvz servermanager.tar.gz servermanager/
rm -R servermanager
