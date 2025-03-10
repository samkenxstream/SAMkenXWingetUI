from PySide6.QtCore import *
import subprocess, time, os, sys, re
from tools import *
from tools import _
from .PackageClasses import *
from .sampleHelper import *


class ChocoPackageManager(SamplePackageManager):
    
    if getSettings("UseSystemChocolatey"):
        EXECUTABLE = "choco.exe"
    else:
        EXECUTABLE = os.path.join(os.path.join(realpath, "choco-cli"), "choco.exe")
        os.environ["chocolateyinstall"] = os.path.dirname(EXECUTABLE)

    icon = None

    NAME = "Chocolatey"
    CACHE_FILE = os.path.join(os.path.expanduser("~"), f".wingetui/cacheddata/{NAME}CachedPackages")
    CACHE_FILE_PATH = os.path.join(os.path.expanduser("~"), ".wingetui/cacheddata")

    BLACKLISTED_PACKAGE_NAMES =  ["Did", "Features?", "Validation", "-", "being", "It", "Error", "L'accs", "Maximum", "This", "Output Is Package name ", "'chocolatey'", "Operable"]
    BLACKLISTED_PACKAGE_IDS =  ["Did", "Features?", "Validation", "-", "being", "It", "Error", "L'accs", "Maximum", "This", "Output is package name ", "operable", "Invalid"]
    BLACKLISTED_PACKAGE_VERSIONS =  ["Did", "Features?", "Validation", "-", "being", "It", "Error", "L'accs", "Maximum", "This", "packages", "current version", "installed version", "is", "program", "validations", "argument"]

    Capabilities = PackageManagerCapabilities()
    Capabilities.CanRunAsAdmin = True
    Capabilities.CanSkipIntegrityChecks = True
    Capabilities.CanRunInteractively = True
    Capabilities.CanRemoveDataOnUninstall = False
    Capabilities.SupportsCustomVersions = True
    Capabilities.SupportsCustomArchitectures = True
    Capabilities.SupportsCustomScopes = False
    
    if not os.path.exists(CACHE_FILE_PATH):
        os.makedirs(CACHE_FILE_PATH)
        
    def isEnabled(self) -> bool:
        return not getSettings(f"Disable{self.NAME}")

    def getAvailablePackages(self, second_attempt: bool = False) -> list[Package]:
        f"""
        Will retieve the cached packages for the package manager {self.NAME} in the format of a list[Package] object.
        If the cache is empty, will forcefully cache the packages and return a valid list[Package] object.
        Finally, it will start a background cacher thread.
        """
        print(f"🔵 Starting {self.NAME} search for available packages")
        try:
            packages: list[Package] = []
            if os.path.exists(self.CACHE_FILE):
                f = open(self.CACHE_FILE, "r", encoding="utf-8", errors="ignore")
                content = f.read()
                f.close()
                if content != "":
                    print(f"🟢 Found valid, non-empty cache file for {self.NAME}!")
                    for line in content.split("\n"):
                        package = line.split(",")
                        if len(package) >= 3 and not package[0] in self.BLACKLISTED_PACKAGE_NAMES and not package[1] in self.BLACKLISTED_PACKAGE_IDS and not package[2] in self.BLACKLISTED_PACKAGE_VERSIONS:
                            packages.append(Package(formatPackageIdAsName(package[0]), package[1], package[2], self.NAME, Choco))
                    Thread(target=self.cacheAvailablePackages, daemon=True, name=f"{self.NAME} package cacher thread").start()
                    print(f"🟢 {self.NAME} search for installed packages finished with {len(packages)} result(s)")
                    return packages
                else:
                    print(f"🟠 {self.NAME} cache file exists but is empty!")
                    if second_attempt:
                        print(f"🔴 Could not load {self.NAME} packages, returning an empty list!")
                        return []
                    self.cacheAvailablePackages()
                    return self.getAvailablePackages(second_attempt = True)
            else:
                print(f"🟡 {self.NAME} cache file does not exist, creating cache forcefully and returning new package list")
                if second_attempt:
                    print(f"🔴 Could not load {self.NAME} packages, returning an empty list!")
                    return []
                self.cacheAvailablePackages()
                return self.getAvailablePackages(second_attempt = True)
        except Exception as e:
            report(e)
            return []
        
    def cacheAvailablePackages(self) -> None:
        """
        INTERNAL METHOD
        Will load the available packages and write them into the cache file
        """
        print(f"🔵 Starting {self.NAME} package caching")
        try:
            p = subprocess.Popen([self.EXECUTABLE, "search", "*"] , stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE, shell=True, env=os.environ.copy())
            ContentsToCache = ""
            while p.poll() is None:
                line: str = str(p.stdout.readline().strip(), "utf-8", errors="ignore")
                if line:
                    if len(line.split(" ")) >= 2:
                        name = formatPackageIdAsName(line.split(" ")[0])
                        id = line.split(" ")[0]
                        version = line.split(" ")[1]
                        
                        if not name in self.BLACKLISTED_PACKAGE_NAMES and not id in self.BLACKLISTED_PACKAGE_IDS and not version in self.BLACKLISTED_PACKAGE_VERSIONS:
                            ContentsToCache += f"{name},{id},{version}\n"
            AlreadyCachedPackages = ""
            try:
                if os.path.exists(self.CACHE_FILE):
                    f = open(self.CACHE_FILE, "r")
                    AlreadyCachedPackages = f.read()
                    f.close()
            except Exception as e:
                report(e)
            for line in AlreadyCachedPackages.split("\n"):
                if line.split(",")[0] not in ContentsToCache:
                    ContentsToCache += line + "\n"
            with open(self.CACHE_FILE, "w") as f:
                f.write(ContentsToCache)
            print(f"🟢 {self.NAME} packages cached successfuly")
        except Exception as e:
            report(e)
            
    def getAvailableUpdates(self) -> list[UpgradablePackage]:
        f"""
        Will retieve the upgradable packages by {self.NAME} in the format of a list[UpgradablePackage] object.
        """
        print(f"🔵 Starting {self.NAME} search for updates")
        try:
            packages: list[UpgradablePackage] = []
            p = subprocess.Popen([self.EXECUTABLE, "outdated"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE, cwd=os.getcwd(), env=os.environ.copy(), shell=True)
            rawoutput = "\n\n---------"
            while p.poll() is None:
                line: str = str(p.stdout.readline().strip(), "utf-8", errors="ignore")
                rawoutput += "\n"+line
                if line:
                    
                    if len(line.split("|")) >= 3:
                        #Replace these lines with the parse mechanism
                        name = formatPackageIdAsName(line.split("|")[0])
                        id = line.split("|")[0]
                        version = line.split("|")[1]
                        newVersion = line.split("|")[2]
                        source = self.NAME
                    else:
                        continue
                    
                    if not name in self.BLACKLISTED_PACKAGE_NAMES and not id in self.BLACKLISTED_PACKAGE_IDS and not version in self.BLACKLISTED_PACKAGE_VERSIONS:
                        packages.append(UpgradablePackage(name, id, version, newVersion, source, Choco))
            print(f"🟢 {self.NAME} search for updates finished with {len(packages)} result(s)")
            globals.PackageManagerOutput += rawoutput
            return packages
        except Exception as e:
            report(e)
            return []

    def getInstalledPackages(self) -> list[Package]:
        f"""
        Will retieve the intalled packages by {self.NAME} in the format of a list[Package] object.
        """
        print(f"🔵 Starting {self.NAME} search for installed packages")
        try:
            packages: list[Package] = []
            p = subprocess.Popen([self.EXECUTABLE, "list", "--local-only"] , stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE, cwd=os.getcwd(), env=os.environ.copy(), shell=True)
            rawoutput = "\n\n---------"
            while p.poll() is None:
                line: str = str(p.stdout.readline().strip(), "utf-8", errors="ignore")
                rawoutput += "\n"+line
                if line:
                    if len(line.split(" ")) >= 2:
                        name = formatPackageIdAsName(line.split(" ")[0])
                        id = line.split(" ")[0]
                        version = line.split(" ")[1]
                        source = self.NAME
                        if not name in self.BLACKLISTED_PACKAGE_NAMES and not id in self.BLACKLISTED_PACKAGE_IDS and not version in self.BLACKLISTED_PACKAGE_VERSIONS:
                            packages.append(Package(name, id, version, source, Choco))
            print(f"🟢 {self.NAME} search for installed packages finished with {len(packages)} result(s)")
            globals.PackageManagerOutput += rawoutput
            return packages
        except Exception as e:
            report(e)
            return []
        
    def getPackageDetails(self, package: Package) -> PackageDetails:
        """
        Will return a PackageDetails object containing the information of the given Package object
        """
        print(f"🔵 Starting get info for {package.Name} on {self.NAME}")
        details = PackageDetails(package)
        try:
            p = subprocess.Popen([self.EXECUTABLE, "info", package.Id], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE, cwd=os.getcwd(), env=os.environ.copy(), shell=True)
            output: list[str] = []
            details.ManifestUrl = f"https://community.chocolatey.org/packages/{package.Id}"
            details.Architectures = ["x86"]
            isReadingDescription = False
            isReadingReleaseNotes = False
            while p.poll() is None:
                line = p.stdout.readline()
                if line:
                    output.append(str(line, encoding='utf-8', errors="ignore"))
            for line in output:
                if isReadingDescription:
                    if line.startswith("  "):
                        details.Description += "<br>"+line
                    else:
                        isReadingDescription = False
                        for match in re.findall("\[!\[[^\[\]]*\]\([^\(\)]*\)\]\([^\(\)]*\)", details.Description):
                            details.Description = details.Description.replace(match, f'<a style="color:{blueColor}" href="{match.split("(")[-1][:-1]}">{match.split("]")[0][3:]}</a>')

                        for match in re.findall("\[[^\[\]]*\]\([^\(\)]*\)", details.Description):
                            details.Description = details.Description.replace(match, f'<a style="color:{blueColor}" href="{match.split("]")[0][1:-1]}">{match.split("]")[0][1:]}</a>')
                        
                        for match in re.findall("#{2,4}[^\>\<]*<br>", details.Description):
                            details.Description = details.Description.replace(match, f'<b>{match.replace("#", "").strip()}</b>')
                        
                if isReadingReleaseNotes:
                    if line.startswith("  "):
                        details.ReleaseNotes += "<br>"+line
                    else:
                        isReadingReleaseNotes = False
                        for match in re.findall("\[!\[[^\[\]]*\]\([^\(\)]*\)\]\([^\(\)]*\)", details.ReleaseNotes):
                            details.ReleaseNotes = details.ReleaseNotes.replace(match, f'<a style="color:{blueColor}" href="{match.split("(")[-1][:-1]}">{match.split("]")[0][3:]}</a>')

                        for match in re.findall("\[[^\[\]]*\]\([^\(\)]*\)", details.ReleaseNotes):
                            details.ReleaseNotes = details.ReleaseNotes.replace(match, f'<a style="color:{blueColor}" href="{match.split("]")[0][1:-1]}">{match.split("]")[0][1:]}</a>')
                        
                        for match in re.findall("#{2,4}[^\>\<]*<br>", details.ReleaseNotes):
                            details.ReleaseNotes = details.ReleaseNotes.replace(match, f'<b>{match.replace("#", "").strip()}</b>')
                        if details.ReleaseNotes != "":
                            if details.ReleaseNotes != "":
                                details.ReleaseNotesUrl = _("Not available")

                if "Title:" in line:
                    details.Name = line.split("|")[0].replace("Title:", "").strip()
                    details.UpdateDate = line.split("|")[1].replace("Published:", "").strip()
                elif "Author:" in line:
                    details.Author = line.replace("Author:", "").strip()
                elif "Software Site:" in line:
                    details.HomepageURL = line.replace("Software Site:", "").strip()
                elif "Software License:" in line:
                    details.LicenseURL = line.replace("Software License:", "").strip()
                elif "Package Checksum:" in line:
                    details.InstallerHash = "<br>"+(line.replace("Package Checksum:", "").strip().replace("'", "").replace("(SHA512)", ""))
                elif "Description:" in line:
                    details.Description = line.replace("Description:", "").strip()
                    isReadingDescription = True
                elif "Release Notes" in line:
                    details.ReleaseNotesUrl = line.replace("Release Notes:", "").strip()
                    details.ReleaseNotes = ""
                    isReadingReleaseNotes = True
                elif "Tags" in line:
                    details.Tags = [tag for tag in line.replace("Tags:", "").strip().split(" ") if tag != ""]
            details.Versions = []
            p = subprocess.Popen([self.EXECUTABLE, "find", "-e", package.Id, "-a"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE, cwd=os.getcwd(), env=os.environ.copy(), shell=True)
            print(f"🟢 Starting get info for id {package.Id}")
            output = []
            while p.poll() is None:
                line = p.stdout.readline().strip()
                if line:
                    output.append(str(line, encoding='utf-8', errors="ignore"))
            for line in output:
                details.Versions.append(line.split(" ")[1])
            print(f"🟢 Get info finished for {package.Name} on {self.NAME}")
            return details
        except Exception as e:
            report(e)
            return details
    
    def getIcon(self, source: str) -> QIcon:
        if not self.icon:
            self.icon = QIcon(getMedia("choco"))
        return self.icon
    
    def getParameters(self, options: InstallationOptions) -> list[str]:
        Parameters: list[str] = []
        if options.Architecture:
            if options.Architecture == "x86":
                Parameters.append("--forcex86")
        if options.CustomParameters:
            Parameters += options.CustomParameters
        if options.InteractiveInstallation:
            Parameters.append("--notsilent")
        if options.SkipHashCheck:
            Parameters += ["--ignore-checksums", "--force"]
        if options.Version:
            Parameters += ["--version="+options.Version, "--allow-downgrade"]
        return Parameters

    def startInstallation(self, package: Package, options: InstallationOptions, widget: InstallationWidgetType) -> subprocess.Popen:
        Command = [self.EXECUTABLE, "install", package.Id, "-y"] + self.getParameters(options)
        if options.RunAsAdministrator:
            Command = [GSUDO_EXECUTABLE] + Command
        print(f"🔵 Starting {package} installation with Command", Command)
        p = subprocess.Popen(Command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE, shell=True, cwd=GSUDO_EXE_LOCATION, env=os.environ.copy())
        Thread(target=self.installationThread, args=(p, options, widget,), name=f"{self.NAME} installation thread: installing {package.Name}").start()
        return p
        
    def startUpdate(self, package: Package, options: InstallationOptions, widget: InstallationWidgetType) -> subprocess.Popen:
        Command = [self.EXECUTABLE, "upgrade", package.Id, "-y"] + self.getParameters(options)
        if options.RunAsAdministrator:
            Command = [GSUDO_EXECUTABLE] + Command
        print(f"🔵 Starting {package} update with Command", Command)
        p = subprocess.Popen(Command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE, shell=True, cwd=GSUDO_EXE_LOCATION, env=os.environ.copy())
        Thread(target=self.installationThread, args=(p, options, widget,), name=f"{self.NAME} installation thread: updating {package.Name}").start()
        return p

    def installationThread(self, p: subprocess.Popen, options: InstallationOptions, widget: InstallationWidgetType):
        output = ""
        counter = 0
        p.stdin = b"\r\n"
        while p.poll() is None:
            line = str(p.stdout.readline(), encoding='utf-8', errors="ignore").strip()
            if line:
                widget.addInfoLine.emit(line)
                counter += 1
                widget.counterSignal.emit(counter)
                output += line+"\n"
        p.wait()
        outputCode = p.returncode
        if outputCode in (1641, 3010):
            outputCode = RETURNCODE_OPERATION_SUCCEEDED
        elif outputCode == 3010:
            outputCode = RETURNCODE_NEEDS_RESTART
        elif ("Run as administrator" in output or "The requested operation requires elevation" in output or 'ERROR: Exception calling "CreateDirectory" with "1" argument(s): "Access to the path' in output) and outputCode != 0:
            outputCode = RETURNCODE_NEEDS_ELEVATION
        widget.finishInstallation.emit(outputCode, output)

    def startUninstallation(self, package: Package, options: InstallationOptions, widget: InstallationWidgetType) -> subprocess.Popen:
        Command = [self.EXECUTABLE, "uninstall", package.Id, "-y"] + self.getParameters(options)
        if options.RunAsAdministrator:
            Command = [GSUDO_EXECUTABLE] + Command
        print(f"🔵 Starting {package} uninstall with Command", Command)
        p = subprocess.Popen(Command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE, shell=True, cwd=GSUDO_EXE_LOCATION, env=os.environ.copy())
        Thread(target=self.uninstallationThread, args=(p, options, widget,), name=f"{self.NAME} installation thread: uninstalling {package.Name}").start()
        return p

    def uninstallationThread(self, p: subprocess.Popen, options: InstallationOptions, widget: InstallationWidgetType):
        outputCode = RETURNCODE_OPERATION_SUCCEEDED
        counter = 0
        output = ""
        p.stdin = b"\r\n"
        while p.poll() is None:
            line = p.stdout.readline()
            line = line.strip()
            line = str(line, encoding='utf-8', errors="ignore").strip()
            if line:
                widget.addInfoLine.emit(line)
                counter += 1
                widget.counterSignal.emit(counter)
                output += line+"\n"
        p.wait()
        outputCode = p.returncode
        if outputCode in (1605, 1614, 1641):
            outputCode = RETURNCODE_OPERATION_SUCCEEDED
        elif outputCode == 3010:
            outputCode = RETURNCODE_NEEDS_RESTART
        elif "Run as administrator" in output or "The requested operation requires elevation" in output:
            outputCode = RETURNCODE_NEEDS_ELEVATION
        widget.finishInstallation.emit(outputCode, output)
        
    def detectManager(self, signal: Signal = None) -> None:
        o = subprocess.run(f"{self.EXECUTABLE} -v", shell=True, stdout=subprocess.PIPE)
        globals.componentStatus[f"{self.NAME}Found"] = shutil.which(self.EXECUTABLE) != None
        globals.componentStatus[f"{self.NAME}Version"] = o.stdout.decode('utf-8').replace("\n", "")
        if signal:
            signal.emit()
        
    def updateSources(self, signal: Signal = None) -> None:
        pass # Handled by the package manager, no need to manually reload
        if signal:
            signal.emit()

Choco = ChocoPackageManager()


if(__name__=="__main__"):
    import __init__