:: ungoogled-chromium Windows build script

set DEPOT_TOOLS_WIN_TOOLCHAIN=0

:: TODO: Chromium somehow knows which vcvars*.bat to invoke. Perhaps it's possible to use that code here?
:: Set proper Visual Studio environment variables to build GN
FOR /F "tokens=* USEBACKQ" %%F IN (`"%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe" -latest -property installationPath`) DO (
SET VS_PATH=%%F
)

call "%VS_PATH%\VC\Auxiliary\Build\vcvars64.bat"

:: Make %TMP% and %TEMP% directories so Ninja won't fail
mkdir %TMP%
mkdir %TEMP%

cd "%~dp0/.."
mkdir out/Default
copy ungoogled_packaging\args.gn out/Default

path %PATH%;%cd%\third_party\ninja
call python tools\gn\bootstrap\bootstrap.py -o out/Default\gn.exe -s
call out/Default\gn.exe gen out/Default --fail-on-unused-args
call third_party\ninja\ninja.exe -C out/Default chrome chromedriver
