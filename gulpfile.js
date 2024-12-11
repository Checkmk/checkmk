

const chokidar = require('chokidar'),
    exec = require('child_process').exec,
    glob = require('glob').glob;

const DIR_CONF = require("./.gulpconf.json");
const DIR_KEYS = Object.keys(DIR_CONF);

var dirs = [];
var dirs2watch = [];

omdApacheRestart = () => {
    console.log('Restarting OMD Apache...');

    console.log('NOT AVAILABLE! Restart manually: "sudo omd su heute && omd restart apache"');
    // exec('sudo omd su heute && omd restart apache', (err, stdout, stderr) => {
    //     console.error(stderr);
    //     console.log(stdout);
    //     if (err === null) {
    //         console.log('Done!');
    //     }
    //     else {
    //         console.error('ERROR on Restarting OMD Apache!');
    //     }
    //     if (typeof cb === 'function')
    //         cb(err);
    // });
}

matchDirs = (path) => {
    return dirs.filter((d) => {
        return d.indexOf(path) === 0;
    });
}

matchFileDir = (file) => {
    return dirs.filter((d) => {
        return file.indexOf(d) === 0;
    });
};

f12s = async (paths) => {
    return new Promise(async (resolve) => {
        for (const path of paths) {
            await f12(path);
        }
        resolve();
    });
}

f12 = async (path) => {
    return new Promise((resolve) => {
        console.log('f12 in', path);
        exec('cd ' + path + ' && f12', (err, stdout, stderr) => {
            console.error(stderr);
            console.log(stdout);
            if (err === null) {
                console.log('f12 done');
            } else {
                console.error(err);
            }


            resolve(err);
        });
    });
}


detectF12 = async () => {
    return new Promise(async (resolve) => {
        dirs = (await glob(['./**/.f12'])).map((f) => f.replace('/.f12', ''));
        dirs.sort();
        resolve()
    });

};


watchDirs = () => {
    return new Promise((resolve) => {

        watcher = chokidar.watch(dirs2watch, { ignoreInitial: true });
        console.log('Watching directories:', dirs2watch);

        watcher.on('all', (event, file) => {
            f12(matchFileDir(file), (err) => {
                console.log(file, event);
                if (err === null && event === 'add') {
                    {
                        omdApacheRestart();
                    }
                }
            });
        });
    });

}

prepareDirs = (dirs) => {
    dirs2watch = dirs2watch.concat(dirs);
}


input = async (msg) => {
    console.log(msg);
    return new Promise((resolve) => {
        process.stdin.on("data", data => {
            resolve(data.toString().replace('\n', ''));
        })
    });
}

getDirConfByNum = (num) => {
    return DIR_CONF[DIR_KEYS[num - 1]];
}

prepareSelection = (sel) => {

    sel = sel.split(' ');
    if (sel.indexOf('0') >= 0) {
        for (var d of DIR_KEYS) {
            prepareDirs(matchDirs(DIR_CONF[d]));
        }
    } else {
        sel.filter(e => e !== '').forEach(num => {
            console.log('Preparing ', getDirConfByNum(num).desc);
            prepareDirs(matchDirs(getDirConfByNum(num).dir))
        });
    }


}



exports.default = async () => {
    console.log('start default')
    await detectF12();

    console.log('What do you want to f12 automatically?\n');



    var i = 1;
    for (var d of DIR_KEYS) {
        console.log('[' + i++ + ']', DIR_CONF[d].desc);
    }
    console.log('\n[0] All\n');

    prepareSelection(await input('\nSelect directory number(s) to keep in sync (e.g.: "1 3 4"):'));


    var yn = await input('\nRun initial f12 for specified directories? [y/n]:');
    if (yn === 'y') {
        await f12s(dirs2watch);
    }

    await watchDirs();


}
