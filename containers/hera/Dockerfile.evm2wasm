from holiman/hera

RUN rm -rf evm2wasm && \
          git clone --recursive https://github.com/jwasinger/evm2wasm -b charge-by-evm-op-enabled-with-endian-swap --single-branch && \
          cd evm2wasm && \
          npm install && \
          cd tools/wabt && \
          cmake -DBUILD_TESTS=OFF && \
          make -j8

ENV PATH="${PATH}:/evm2wasm/bin"
